# Otomatik varış: rotadaki müşteriye varınca ziyaret kendisi başlar; geçip gidince, kötü konumda, Geri al sonrası başlamaz. Harita bağlantıları ve mavi nokta.
import os
import asyncio,json
from urllib.parse import unquote
from playwright.async_api import async_playwright
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"qa.py")).read().split("TABS=")[0])
FAR={"latitude":40.2,"longitude":31.5}
async def run(W):
    async with async_playwright() as p:
        b=await p.chromium.launch()
        ctx=await b.new_context(timezone_id="Europe/Istanbul",viewport={"width":W,"height":900},geolocation=FAR,permissions=["geolocation"])
        await setup(ctx)
        await ctx.add_init_script("document.addEventListener('click',e=>{const a=e.target.closest('a[href]');if(a&&!/^https?:\\/\\/127/.test(a.href))e.preventDefault()},true);window.open=()=>null;")
        pg=await ctx.new_page();errs=[];pg.on("pageerror",lambda e:errs.append(str(e)[:160]))
        await pg.goto("http://127.0.0.1:8767/boot.html");await pg.wait_for_timeout(1500)
        await pg.click("[data-act=sample]");await pg.wait_for_timeout(300)
        C=await pg.evaluate("custList().filter(hasGeo).reduce((a,c)=>a.every(o=>km(o,c)>0.5)?[...a,c]:a,[]).slice(0,4).map(c=>({id:c.id,name:c.name,lat:c.lat,lng:c.lng}))")
        assert len(C)>=4,C
        at=lambda c:{"latitude":c["lat"],"longitude":c["lng"]}
        ev=pg.evaluate;wait=pg.wait_for_timeout
        await ev("(ids)=>{U.tab='rota';U.selected=new Set(ids);U.arrDwell=300;U.arrFixMs=100;keepUI();render()}",[c["id"] for c in C]);await wait(300)
        R={}
        R["uzaktayken başlamıyor"]=await ev("!U.arrived&&!U.live")
        # varış: önce sorar, kısa süre sonra kendisi başlar
        await ev("U.arrDwell=1200");await ctx.set_geolocation(at(C[0]));await wait(500)
        R["vardın bandı"]=await ev("U.arrived")==C[0]["id"] and "Şimdi başlat" in await ev("document.querySelector('#arrBanner').innerText") and await ev("!U.live")
        await wait(1500)
        R["ziyaret kendisi başladı"]=await ev("U.live&&U.live.customerId")==C[0]["id"]
        R["başlangıç saati var"]=await ev("/^\\d\\d:\\d\\d$/.test(U.live.start)")
        R["bant kapandı, panel açık"]=await ev("!document.querySelector('#arrBanner')&&document.querySelector('.panel.live').innerText.includes('Ziyarette')")
        R["Geri al mesajı"]="kendiliğinden başladı" in await ev("document.querySelector('#toast').innerText")
        # uygulama yeniden açılınca ziyaret kaybolmaz
        await pg.reload();await wait(1200)
        R["yenileyince ziyaret duruyor"]=await ev("U.live&&U.live.customerId")==C[0]["id"]
        await ev("U.arrDwell=300;U.arrFixMs=100")
        # açık ziyaret varken başka müşteriye varış: üstüne yazmaz
        await ctx.set_geolocation(at(C[1]));await wait(800)
        R["açık ziyaret korunuyor"]=await ev("U.live.customerId")==C[0]["id"] and "hâlâ açık" in await ev("document.querySelector('#arrBanner').innerText")
        # Vazgeç: aynı yerde yeniden başlamaz
        await ev("arrivalClear();render()")
        await ctx.set_geolocation(at(C[0]));await wait(200)
        await pg.click(".panel.live [data-act=cancelLive]");await wait(200)
        await ctx.set_geolocation({"latitude":C[0]["lat"]+0.0002,"longitude":C[0]["lng"]});await wait(700)
        R["Vazgeç sonrası yeniden başlamıyor"]=await ev("!U.live&&!U.arrived")
        # Geri al: yeniden başlamaz
        await ctx.set_geolocation(at(C[1]));await wait(800)
        R["ikinci müşteride başladı"]=await ev("U.live&&U.live.customerId")==C[1]["id"]
        await pg.click("#toast button");await wait(200)
        await ctx.set_geolocation({"latitude":C[1]["lat"]+0.0002,"longitude":C[1]["lng"]});await wait(700)
        R["Geri al sonrası başlamıyor"]=await ev("!U.live&&!U.arrived")
        # Başlatma düğmesi
        await ev("U.arrDwell=5000");await ctx.set_geolocation(at(C[2]));await wait(300)
        await pg.click("#arrBanner [data-act=arrClose]");await wait(200)
        await ctx.set_geolocation({"latitude":C[2]["lat"]+0.0002,"longitude":C[2]["lng"]});await wait(300)
        R["Başlatma düğmesi soruyu kapatır"]=await ev("!U.arrived&&!U.live")
        # araçla geçip gitme, kötü konum, uzaklaşma
        P="{lat:%s,lng:%s"%(C[3]["lat"],C[3]["lng"])
        await ctx.set_geolocation(FAR);await wait(200)
        await ev("arrivalCheck(%s,speed:14})"%P);R["araçla geçerken saymıyor"]=await ev("!U.arrived")
        await ev("arrivalCheck(%s,acc:500})"%P);R["kötü konumda saymıyor"]=await ev("!U.arrived")
        await ev("U.arrDwell=400");await ev("arrivalCheck(%s,acc:10,speed:0})"%P);R["durunca sayıyor"]=await ev("U.arrived")==C[3]["id"]
        await wait(800)   # gerçek konum uzakta: bekleme sonunda başlamamalı
        R["uzaklaşınca başlamıyor"]=await ev("!U.arrived&&!U.live")
        # ayar kapalıyken yalnızca sorar
        await ev("U.dayOpen=true;render()");await wait(100)
        await pg.click("[data-act=autoVisit]");await wait(300)
        R["ayar kapandı"]=await ev("day().autoVisit===false")
        R["ayar yazısı"]="Kapalı" in await ev("document.querySelector('[data-act=autoVisit]').innerText")
        await ev("U.arrDwell=200");await ctx.set_geolocation(at(C[3]));await wait(700)
        R["kapalıyken yalnızca soruyor"]=await ev("U.arrived")==C[3]["id"] and await ev("!U.live") and "Ziyareti başlat" in await ev("document.querySelector('#arrBanner').innerText")
        await ev("arrivalClear();saveDay({autoVisit:true})");await wait(200)
        # başka sekmedeyken de çalışır
        await ctx.set_geolocation(FAR);await wait(200);await ev("U.arrSkip=null;U.tab='harita';U.detail=null;render()");await wait(300)
        await ctx.set_geolocation(at(C[3]));await wait(900)
        R["başka sekmede de başlıyor"]=await ev("U.live&&U.live.customerId")==C[3]["id"]
        # harita: mavi nokta konumla kayar
        me0=await ev("(()=>{const e=document.querySelector('#mapSvg .me');return e&&e.style.left+e.style.top})()")
        await ctx.set_geolocation({"latitude":C[3]["lat"]+0.002,"longitude":C[3]["lng"]+0.002});await wait(400)
        me1=await ev("(()=>{const e=document.querySelector('#mapSvg .me');return e&&e.style.left+e.style.top})()")
        R["haritada mavi nokta hareket ediyor"]=bool(me0) and me0!=me1
        await ev("U.live=null;keepUI();U.tab='rota';render()");await wait(100)
        # harita bağlantıları: seçilen uygulama ve doğru hedef
        c=C[0];pt=f'{c["lat"]},{c["lng"]}'
        L=await ev("(id)=>{const c=S.customers.get(id);return {g:navUrl(c,'google'),y:navUrl(c,'yandex'),a:navUrl(c,'apple')}}",c["id"])
        R["Google doğru hedef"]=L["g"].startswith("https://www.google.com/maps/dir/?api=1&travelmode=driving&destination=") and pt in unquote(L["g"])
        R["Yandex doğru hedef"]=L["y"]==f'https://yandex.com.tr/maps/?rtext=~{pt}&rtt=auto'
        R["Apple doğru hedef"]=L["a"].startswith("https://maps.apple.com/?daddr=") and pt in unquote(L["a"]) and L["a"].endswith("dirflg=d")
        await ev("saveDay({mapApp:'yandex',lunchPlaces:[{name:'Test Lokanta',lat:41.01,lng:28.9}]})");await wait(200);await ev("U.dayOpen=true;render()");await wait(150)
        R["öğle yeri de seçilen haritada"]=await ev("[...document.querySelectorAll('#dayDetails a')].filter(a=>a.textContent==='Harita').every(a=>a.href.includes('yandex.com.tr'))&&[...document.querySelectorAll('#dayDetails a')].some(a=>a.textContent==='Harita')")
        R["yatay taşma yok"]=await ev("document.documentElement.scrollWidth")<=W
        await b.close()
        print(W,json.dumps(R,ensure_ascii=False))
        return [f"{W}:{k}" for k,v in R.items() if v is False],errs
async def main():
    bad=[];er=[]
    for W in (390,320):
        x,y=await run(W);bad+=x;er+=y
    print("HATALAR",bad);print("JS HATALARI:",er)
asyncio.run(main())
