# Harita servisi yedekleri: ana Overpass sunucusu hata verirse yedek sunucuya geçilir; hepsi çökerse anlaşılır uyarı çıkar.
import os
import asyncio,json,sys
from playwright.async_api import async_playwright
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"qa.py")).read().split("TABS=")[0])
BODY=json.dumps({"elements":[{"type":"node","lat":41.019,"lon":28.909,"tags":{"shop":"car_parts","name":"Yedek Sunucu Oto"}}]})
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        ctx=await b.new_context(timezone_id="Europe/Istanbul",viewport={"width":390,"height":800},geolocation={"latitude":41.0186,"longitude":28.9078},permissions=["geolocation"])
        await setup(ctx)
        mode={"m":"yedek"};hits=[]
        async def main_srv(r): hits.append("ana");await r.fulfill(status=504 if mode["m"]!="ana" else 200,headers=H,content_type="application/json",body=BODY if mode["m"]=="ana" else "")
        async def mirror(r): hits.append("yedek");await (r.fulfill(status=200,headers=H,content_type="application/json",body=BODY) if mode["m"]=="yedek" else r.fulfill(status=429,headers=H,body=""))
        async def other(r): hits.append("diğer");await r.abort()
        await ctx.unroute("https://overpass-api.de/**");await ctx.route("https://overpass-api.de/**",main_srv)
        await ctx.route("https://overpass.private.coffee/**",mirror)
        await ctx.route("https://maps.mail.ru/**",other);await ctx.route("https://overpass.kumi.systems/**",other)
        await ctx.route("https://tile.openstreetmap.org/**",lambda r:r.abort())
        pg=await ctx.new_page();errs=[];pg.on("pageerror",lambda e:errs.append(str(e)[:160]))
        await pg.goto("http://127.0.0.1:8767/boot.html");await pg.wait_for_timeout(1500)
        await pg.click("[data-act=sample]");await pg.wait_for_timeout(300)
        R={}
        await pg.evaluate("localStorage.removeItem('saha-overpass');U.tab='yakin';U.detail=null;render()")
        await pg.click("#app [data-act=findPros]");await pg.wait_for_timeout(1500)
        R["ana çökünce yedekten bulundu"]=await pg.evaluate("!!(U.prospects&&U.prospects.list.some(x=>x.name==='Yedek Sunucu Oto'))")
        R["hata gösterilmedi"]=await pg.evaluate("!(U.prospects&&U.prospects.err)")
        R["çalışan sunucu hatırlandı"]=await pg.evaluate("localStorage.getItem('saha-overpass')")=="https://overpass.private.coffee/api/interpreter"
        hits.clear()
        await pg.evaluate("findProspects(3000)");await pg.wait_for_timeout(1200)
        R["ikinci aramada önce yedek denendi"]=bool(hits) and hits[0]=="yedek"
        mode["m"]="hepsi";hits.clear()
        await pg.evaluate("findProspects(3000)");await pg.wait_for_timeout(1500)
        err=await pg.evaluate("(U.prospects&&U.prospects.err)||''")
        R["hepsi çökünce anlaşılır uyarı"]="yanıt vermiyor" in err and "tekrar dene" in err
        R["tüm sunucular denendi"]=set(hits)>={"ana","yedek","diğer"}
        R["uyarı ekranda"]=await pg.evaluate("document.querySelector('#sheet').innerText.includes('yanıt vermiyor')")
        await b.close()
        bad=[k for k,v in R.items() if v is False]
        print(json.dumps(R,ensure_ascii=False));print("HATALAR",bad);print("JS HATALARI:",errs)
asyncio.run(main())
