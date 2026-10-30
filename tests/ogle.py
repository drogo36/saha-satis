# Öğle arası: yakındaki yemek yerlerini uygulama kendisi bulur; ✓ ile TokenFlex yerlerine kaydedilir, ✗ ile bir daha önerilmez (geri alınabilir).
import os
import asyncio,json
from playwright.async_api import async_playwright
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"qa.py")).read().split("TABS=")[0])
FOOD={"elements":[{"type":"node","lat":41.0190,"lon":28.9080,"tags":{"amenity":"restaurant","name":"Hacı Usta Lokantası"}},
 {"type":"way","center":{"lat":41.0200,"lon":28.9100},"tags":{"amenity":"fast_food","name":"Köşe Büfe"}},
 {"type":"node","lat":41.0170,"lon":28.9050,"tags":{"amenity":"cafe","name":"Mavi Kafe"}},
 {"type":"node","lat":41.0175,"lon":28.9060,"tags":{"amenity":"cafe"}}]}
async def run(W):
    async with async_playwright() as p:
        b=await p.chromium.launch()
        ctx=await b.new_context(viewport={"width":W,"height":900},geolocation={"latitude":41.0186,"longitude":28.9078},permissions=["geolocation"])
        await setup(ctx);calls=[]
        async def ov(r):
            calls.append(r.request.post_data or "");await r.fulfill(status=200,headers=H,content_type="application/json",body=json.dumps(FOOD))
        await ctx.unroute("https://overpass-api.de/**");await ctx.route("https://overpass-api.de/**",ov)
        await ctx.add_init_script("document.addEventListener('click',e=>{const a=e.target.closest('a[href]');if(a&&!/^https?:\\/\\/127/.test(a.href))e.preventDefault()},true);window.open=()=>null;")
        pg=await ctx.new_page();errs=[];pg.on("pageerror",lambda e:errs.append(str(e)[:160]))
        await pg.goto("http://127.0.0.1:8767/boot.html");await pg.wait_for_timeout(1500)
        await pg.click("[data-act=sample]");await pg.wait_for_timeout(300)
        await pg.evaluate("saveDay({lunchPlaces:[]})");await pg.evaluate("U.tab='rota';U.lunch.open=true;render()");await pg.wait_for_timeout(200)
        R={}
        await pg.click("[data-act=lunchLocate]");await pg.wait_for_timeout(900)
        R["kendisi aradı (yemek yerleri)"]=len(calls)>0 and "restaurant" in calls[0]
        txt=await pg.evaluate("document.querySelector('#ogle').innerText")
        R["öneriler listelendi"]=all(n in txt for n in ["Hacı Usta Lokantası","Köşe Büfe","Mavi Kafe"])
        R["en yakın en üstte"]=txt.index("Hacı Usta")<txt.index("Mavi Kafe")
        R["türü yazıyor"]=await pg.evaluate("[...document.querySelectorAll('#ogle .chip')].some(c=>c.textContent==='Büfe / hızlı yemek')")
        n0=await pg.evaluate("document.querySelectorAll('#ogle [data-act=lunchYes]').length")
        await pg.click("#ogle [data-act=lunchNo] >> nth=1");await pg.wait_for_timeout(300)
        R["✗ sonrası önerilmiyor"]=await pg.evaluate("(day().lunchNo||[]).length===1&&document.querySelectorAll('#ogle [data-act=lunchYes]').length===%d"%(n0-1))
        await pg.click("#toast button");await pg.wait_for_timeout(300)
        R["✗ geri alındı"]=await pg.evaluate("(day().lunchNo||[]).length===0")
        await pg.click("#ogle [data-act=lunchYes] >> nth=0");await pg.wait_for_timeout(400)
        R["✓ belleğe kaydedildi"]=await pg.evaluate("JSON.stringify(day().lunchPlaces)")
        R["✓ sonrası kayıtlı yer gösteriliyor"]=await pg.evaluate("document.querySelector('#ogle').innerText.includes('Hacı Usta Lokantası')&&!!document.querySelector('#ogle a.btn.pri')")
        await pg.reload();await pg.wait_for_timeout(1200)
        R["yenileyince duruyor"]=await pg.evaluate("(day().lunchPlaces||[]).some(p=>p.name==='Hacı Usta Lokantası')")
        # rotada öğle durağı olarak kullanılıyor
        await pg.evaluate("U.tab='rota';U.selected=new Set(custList().filter(hasGeo).slice(0,6).map(c=>c.id));render()");await pg.wait_for_timeout(300)
        R["rota öğle durağı"]=await pg.evaluate("(()=>{const r=buildRoute();return r.plan.lunch?(r.plan.lunch.place?r.plan.lunch.place.name:'yok'):'öğle yok'})()")
        # kayıtlı yer yokken rotada "Yer öner"
        await pg.evaluate("saveDay({lunchPlaces:[]})");await pg.wait_for_timeout(300);await pg.evaluate("U.lunch={pos:null,busy:false,err:'',open:false,cand:null};render()")
        has=await pg.evaluate("!!document.querySelector('[data-act=lunchAt]')")
        R["rotada Yer öner düğmesi"]=has
        if has:
            await pg.click("[data-act=lunchAt]");await pg.wait_for_timeout(700)
            R["Yer öner listeyi açtı"]=await pg.evaluate("document.querySelectorAll('#ogle [data-act=lunchYes]').length>0")
        R["yatay taşma yok"]=await pg.evaluate("document.documentElement.scrollWidth")<=W
        await b.close()
        print(W,json.dumps(R,ensure_ascii=False))
        bad=[f"{W}:{k}" for k,v in R.items() if v is False]
        if R["rota öğle durağı"] in ("yok",): bad.append(f"{W}:rota öğle durağı")
        if "Hacı Usta" not in str(R["✓ belleğe kaydedildi"]): bad.append(f"{W}:kayıt")
        return bad,errs
async def main():
    bad=[];er=[]
    for W in (390,320):
        x,y=await run(W);bad+=x;er+=y
    print("HATALAR",bad);print("JS HATALARI:",er)
asyncio.run(main())
