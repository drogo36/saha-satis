# Yakındaki potansiyeller: aramaya basınca üstte ortalı harita penceresi açılır, konum ve bulunan işletmeler görünür.
import os
import asyncio,json,sys
from playwright.async_api import async_playwright
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"qa.py")).read().split("TABS=")[0])
PNG=bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360f8cf000000020001e221bc330000000049454e44ae426082")
async def run(W):
    async with async_playwright() as p:
        b=await p.chromium.launch()
        ctx=await b.new_context(timezone_id="Europe/Istanbul",viewport={"width":W,"height":800},geolocation={"latitude":41.0186,"longitude":28.9078},permissions=["geolocation"])
        await setup(ctx)
        tiles=[]
        async def tile(r): tiles.append(r.request.url);await r.fulfill(status=200,headers=H,content_type="image/png",body=PNG)
        await ctx.route("https://tile.openstreetmap.org/**",tile)
        await ctx.add_init_script("document.addEventListener('click',e=>{const a=e.target.closest('a[href]');if(a&&!/^https?:\\/\\/127/.test(a.href))e.preventDefault()},true);window.open=()=>null;")
        pg=await ctx.new_page();errs=[];pg.on("pageerror",lambda e:errs.append(str(e)[:160]))
        await pg.goto("http://127.0.0.1:8767/boot.html");await pg.wait_for_timeout(1500)
        await pg.click("[data-act=sample]");await pg.wait_for_timeout(300)
        await pg.evaluate("U.tab='yakin';U.detail=null;render()")
        R={}
        await pg.click("#app [data-act=findPros]");await pg.wait_for_timeout(900)
        R["pencere açıldı"]=await pg.evaluate("!!document.querySelector('#sheet .sheet.pop #nearMap')")
        box=await pg.evaluate("(()=>{const r=document.querySelector('#sheet .sheet.pop').getBoundingClientRect();return {l:r.left,r:innerWidth-r.right,t:r.top,b:innerHeight-r.bottom,w:r.width}})()")
        R["üstte"]=box["t"]<40 and box["b"]>100
        R["ortalı"]=abs(box["l"]-box["r"])<2 and box["l"]>=8
        me=await pg.evaluate("(()=>{const m=document.querySelector('#nearMap .me').getBoundingClientRect(),a=document.querySelector('#nearMap').getBoundingClientRect();return [Math.round(m.left+m.width/2-a.left-a.width/2),Math.round(m.top+m.height/2-a.top-a.height/2)]})()")
        R["konum ortada"]=abs(me[0])<=2 and abs(me[1])<=2
        R["harita karoları"]=len(tiles)>0 and all("/12/" in u or "/13/" in u or "/11/" in u for u in tiles)
        R["işletme iğnesi"]=await pg.evaluate("document.querySelectorAll('#nearMap .pin.pr').length")
        R["kayıtlı müşteri noktası"]=await pg.evaluate("document.querySelectorAll('#nearMap .pin.cu').length>0")
        R["telif yazısı"]=await pg.evaluate("document.querySelector('#nearMap .att').innerText.includes('OpenStreetMap')")
        R["yatay taşma yok"]=await pg.evaluate("document.documentElement.scrollWidth")<=W
        await pg.click("#nearMap .pin.pr");await pg.wait_for_timeout(200)
        R["iğneye dokununca bilgi"]=await pg.evaluate("document.querySelector('#sheet').innerText.includes('Yıldırım Oto Parça')")
        await pg.click("#sheet [data-act=addPros]");await pg.wait_for_timeout(400)
        R["haritadan aday eklendi"]=await pg.evaluate("custList().some(c=>c.name==='Yıldırım Oto Parça')")
        await pg.click("#sheet .sheet [data-act=closeSheet] >> nth=-1");await pg.wait_for_timeout(200)
        R["kapandı"]=await pg.evaluate("!document.querySelector('#sheet .sheet')")
        R["tekrar aç düğmesi"]=await pg.evaluate("!!document.querySelector('#app [data-act=nmOpen]')")
        await pg.click("#app [data-act=nmOpen]");await pg.wait_for_timeout(200)
        R["tekrar açıldı"]=await pg.evaluate("!!document.querySelector('#sheet #nearMap')")
        await b.close()
        bad=[k for k,v in R.items() if v is False or v==0]
        print(W,json.dumps(R,ensure_ascii=False))
        return bad,errs
async def main():
    allbad=[];allerr=[]
    for W in (390,320):
        bad,errs=await run(W);allbad+=[f"{W}:{k}" for k in bad];allerr+=errs
    print("HATALAR",allbad);print("JS HATALARI:",allerr)
asyncio.run(main())
