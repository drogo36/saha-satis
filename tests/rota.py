# Rotaya başla (ilk müşteriden, ziyaretle ilerler), Google/Yandex/Apple bağlantıları, tercih edilen harita, restoranda yer adını konumdan bulma.
import os
import asyncio,json
from urllib.parse import urlparse,parse_qs
from playwright.async_api import async_playwright
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"qa.py")).read().split("TABS=")[0])
FOOD={"elements":[{"type":"node","lat":41.01880,"lon":28.90790,"tags":{"amenity":"restaurant","name":"Hacı Usta Lokantası"}},
 {"type":"node","lat":41.0170,"lon":28.9050,"tags":{"amenity":"cafe","name":"Mavi Kafe"}}]}
FAR={"elements":[{"type":"node","lat":41.0170,"lon":28.9050,"tags":{"amenity":"cafe","name":"Mavi Kafe"}}]}
IPHONE="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1"
async def run(W):
    async with async_playwright() as p:
        b=await p.chromium.launch()
        ctx=await b.new_context(viewport={"width":W,"height":900},user_agent=IPHONE,geolocation={"latitude":41.0186,"longitude":28.9078},permissions=["geolocation"])
        await setup(ctx);data={"o":FOOD}
        async def ov(r): await r.fulfill(status=200,headers=H,content_type="application/json",body=json.dumps(data["o"]))
        await ctx.unroute("https://overpass-api.de/**");await ctx.route("https://overpass-api.de/**",ov)
        async def nom(r): await r.fulfill(status=200,headers=H,content_type="application/json",body=json.dumps({"name":"Ters Kebap Salonu","address":{"road":"Y Sk","town":"Fatih","province":"İstanbul"}}))
        await ctx.unroute("https://nominatim.openstreetmap.org/**");await ctx.route("https://nominatim.openstreetmap.org/**",nom)
        await ctx.add_init_script("document.addEventListener('click',e=>{const a=e.target.closest('a[href]');if(a&&!/^https?:\\/\\/127/.test(a.href))e.preventDefault()},true);window.open=()=>null;")
        pg=await ctx.new_page();errs=[];pg.on("pageerror",lambda e:errs.append(str(e)[:160]))
        await pg.clock.set_fixed_time("2026-11-04T09:30:00")  # duraklar saate bağlı: test günün her saatinde aynı sonucu versin
        await pg.goto("http://127.0.0.1:8767/boot.html");await pg.wait_for_timeout(1500)
        await pg.click("[data-act=sample]");await pg.wait_for_timeout(300)
        R={}
        await pg.evaluate("U.tab='rota';U.forceAll=true;U.selected=new Set(custList().filter(hasGeo).slice(0,6).map(c=>c.id));render()");await pg.wait_for_timeout(300)
        # bağlantılar
        hrefs=await pg.evaluate("[...document.querySelectorAll('a[href]')].map(a=>a.href)")
        goo=[h for h in hrefs if "/maps/dir/" in h and "waypoints" in h]
        R["telefonda en fazla 3 ara durak"]=bool(goo) and all(len(parse_qs(urlparse(h).query)["waypoints"][0].split("|"))<=3 for h in goo)
        R["boş hedef yok"]=all(parse_qs(urlparse(h).query).get("destination") for h in hrefs if "/maps/dir/" in h)
        R["Yandex rota bağlantısı"]=any("yandex.com.tr/maps/" in h and "rtext=" in h and "rtt=auto" in h for h in hrefs)
        R["Apple bağlantısı"]=any(h.startswith("https://maps.apple.com/?daddr=") and "dirflg=d" in h for h in hrefs)
        # adressiz, konumsuz müşteri bağlantıyı bozmaz
        R["adressiz durak adıyla"]=await pg.evaluate("(()=>{const r={plan:{rows:[]},nogeo:[{name:'Adsız Oto'}],end:null,start:null};return mapsRouteLinks(r)[0].u.includes(encodeURIComponent('Adsız Oto'))})()")
        # rotaya başla
        first=await pg.evaluate("routeStops(buildRoute())[0].name")
        await pg.click("[data-act=tripStart]");await pg.wait_for_timeout(300)
        txt=await pg.evaluate("document.querySelector('#tripCard').innerText")
        R["ilk müşteriden başladı"]=first in txt and "1/" in txt
        R["üç harita düğmesi"]=await pg.evaluate("['google','yandex','apple'].every(k=>document.querySelector(`#tripCard a[data-map=${k}]`))")
        await pg.click("#tripCard [data-act=startLive]");await pg.wait_for_timeout(200)
        R["ziyaret başladı"]=await pg.evaluate("!!U.live")
        await pg.evaluate("U.live=null;render()")
        await pg.reload();await pg.wait_for_timeout(1200)
        R["yenileyince rota sürüyor"]=await pg.evaluate("!!document.querySelector('#tripCard')")
        cur=await pg.evaluate("tripState().cur.id");nxt=await pg.evaluate("tripState().next.id")
        # ziyaret kaydı rotadan çıkarır: sıradakine geçmeli
        await pg.evaluate("U.selected.delete(%s);keepUI();render()"%json.dumps(cur));await pg.wait_for_timeout(200)
        R["sıradakine geçti"]=await pg.evaluate("tripState().cur.id")==nxt and "2/" in await pg.evaluate("document.querySelector('#tripCard').innerText")
        await pg.click("#tripCard [data-act=tripSkip]");await pg.wait_for_timeout(200)
        R["atla çalışıyor"]=await pg.evaluate("tripState().cur.id")!=nxt
        await pg.click("#toast button");await pg.wait_for_timeout(200)
        R["atla geri alındı"]=await pg.evaluate("tripState().cur.id")==nxt
        R["yatay taşma yok (rota)"]=await pg.evaluate("document.documentElement.scrollWidth")<=W
        await pg.evaluate("U.selected=new Set();keepUI();render()");await pg.wait_for_timeout(150)
        R["rota bitti görünüyor"]="Rota bitti" in await pg.evaluate("document.querySelector('#tripCard').innerText")
        await pg.click("#tripCard [data-act=tripEnd]");await pg.wait_for_timeout(150)
        R["kart kapandı"]=await pg.evaluate("!document.querySelector('#tripCard')&&U.trip===null")
        # tercih edilen harita
        await pg.evaluate("U.selected=new Set(custList().filter(hasGeo).slice(0,2).map(c=>c.id));U.dayOpen=true;render()");await pg.wait_for_timeout(200)
        await pg.select_option("#df_map","yandex");await pg.click("#dayForm button[type=submit]");await pg.wait_for_timeout(400)
        R["tercih kaydedildi"]=await pg.evaluate("day().mapApp")=="yandex"
        R["yol tarifi Yandex"]=await pg.evaluate("[...document.querySelectorAll('.item.stop a')].some(a=>a.textContent==='Yol tarifi'&&a.href.includes('yandex.com.tr/maps/?rtext=~'))")
        await pg.evaluate("saveDay({mapApp:'apple'})");await pg.wait_for_timeout(300)
        R["yol tarifi Apple"]=await pg.evaluate("[...document.querySelectorAll('.item.stop a')].some(a=>a.textContent==='Yol tarifi'&&a.href.includes('maps.apple.com'))")
        await pg.evaluate("saveDay({mapApp:undefined})");await pg.wait_for_timeout(300)
        R["eski kayıtta Google"]=await pg.evaluate("mapApp()")=="google"
        # öğle: yer adı
        await pg.evaluate("saveDay({lunchPlaces:[]})");await pg.evaluate("U.selected=new Set();U.lunch.open=true;render()");await pg.wait_for_timeout(200)
        await pg.click("[data-act=lunchLocate]");await pg.wait_for_timeout(900)
        R["buradasın adı buldu"]="Hacı Usta Lokantası" in await pg.evaluate("document.querySelector('#hereGuess').innerText")
        R["kutu dolu"]=await pg.evaluate("document.querySelector('#lh_name').value")=="Hacı Usta Lokantası"
        R["kendiliğinden kaydetmedi"]=await pg.evaluate("(day().lunchPlaces||[]).length")==0
        await pg.click("#hereGuess [data-act=lunchYes]");await pg.wait_for_timeout(400)
        R["tek dokunuşla kaydedildi"]=await pg.evaluate("day().lunchPlaces.some(p=>p.name==='Hacı Usta Lokantası')")
        # yakın yer yoksa adres servisinden ad
        data["o"]=FAR
        await pg.evaluate("saveDay({lunchPlaces:[],lunchNo:[]})");await pg.evaluate("U.lunch={pos:null,busy:false,err:'',open:true,cand:null};render()");await pg.wait_for_timeout(200)
        await pg.click("[data-act=lunchLocate]");await pg.wait_for_timeout(2300)
        R["uzak yer tahmin edilmez"]=await pg.evaluate("!document.querySelector('#hereGuess')")
        R["adres servisinden ad"]=await pg.evaluate("document.querySelector('#lh_name').value")=="Ters Kebap Salonu"
        await pg.fill("#lh_name","Benim Yerim");await pg.evaluate("render()");await pg.wait_for_timeout(150)
        R["yazdığın ad korunuyor"]=await pg.evaluate("document.querySelector('#lh_name').value")=="Benim Yerim"
        R["yatay taşma yok (öğle)"]=await pg.evaluate("document.documentElement.scrollWidth")<=W
        await b.close()
        print(W,json.dumps(R,ensure_ascii=False))
        return [f"{W}:{k}" for k,v in R.items() if v is not True],errs
async def main():
    bad=[];er=[]
    for W in (390,320):
        x,y=await run(W);bad+=x;er+=y
    print("HATALAR",bad);print("JS HATALARI:",er)
asyncio.run(main())
