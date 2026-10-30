# Müşteri haritası: yakındakiler penceresiyle aynı karolu harita, sürükle/yakınlaştır, nokta kartı ve trafik bağlantısı.
import os
import asyncio,json
from playwright.async_api import async_playwright
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"qa.py")).read().split("TABS=")[0])
PNG=bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360f8cf000000020001e221bc330000000049454e44ae426082")
async def run(W):
    async with async_playwright() as p:
        b=await p.chromium.launch()
        ctx=await b.new_context(viewport={"width":W,"height":800},geolocation={"latitude":41.0186,"longitude":28.9078},permissions=["geolocation"])
        await setup(ctx);tiles=[]
        async def tile(r): tiles.append(r.request.url);await r.fulfill(status=200,headers=H,content_type="image/png",body=PNG)
        await ctx.route("https://tile.openstreetmap.org/**",tile)
        await ctx.add_init_script("document.addEventListener('click',e=>{const a=e.target.closest('a[href]');if(a&&!/^https?:\\/\\/127/.test(a.href))e.preventDefault()},true);window.open=()=>null;")
        pg=await ctx.new_page();errs=[];pg.on("pageerror",lambda e:errs.append(str(e)[:160]))
        await pg.goto("http://127.0.0.1:8767/boot.html");await pg.wait_for_timeout(1500)
        await pg.click("[data-act=sample]");await pg.wait_for_timeout(300)
        await pg.evaluate("U.tab='harita';U.detail=null;render()");await pg.wait_for_timeout(400)
        R={}
        R["karolar"]=await pg.evaluate("document.querySelectorAll('#mapSvg img.tl').length")>0 and len(tiles)>0
        R["tüm noktalar görünüyor"]=await pg.evaluate("document.querySelectorAll('#mapSvg [data-pin]').length===mapPoints().length&&mapPoints().length>0")
        R["telif yazısı"]=await pg.evaluate("document.querySelector('#mapSvg .att').innerText.includes('OpenStreetMap')")
        R["trafik bağlantısı"]=await pg.evaluate("document.querySelector('#mapSvg .cm-trf').href.includes('layer=traffic')")
        z0=await pg.evaluate("M.z");await pg.click("[data-act=zin]");await pg.wait_for_timeout(200)
        R["yakınlaştır"]=await pg.evaluate("M.z")==z0+1 and any(f"/{z0+1}/" in u for u in tiles)
        await pg.click("[data-act=zout]");await pg.wait_for_timeout(200);R["uzaklaştır"]=await pg.evaluate("M.z")==z0
        c0=await pg.evaluate("[M.cx,M.cy]");bb=await (await pg.query_selector("#mapSvg")).bounding_box()
        await pg.mouse.move(bb["x"]+60,bb["y"]+60);await pg.mouse.down();await pg.mouse.move(bb["x"]+140,bb["y"]+110,steps=6);await pg.mouse.up();await pg.wait_for_timeout(200)
        c1=await pg.evaluate("[M.cx,M.cy]");R["sürükle"]=c1[0]<c0[0] and c1[1]<c0[1]
        R["sürükleme sonrası kart açılmadı"]=await pg.evaluate("U.mapSel===null")
        await pg.click("[data-act=zreset]");await pg.wait_for_timeout(200);R["sığdır"]=await pg.evaluate("[M.cx,M.cy]")==c0
        pid=await pg.evaluate("document.querySelector('#mapSvg [data-pin]').dataset.pin")
        await pg.evaluate("document.querySelector('#mapSvg [data-pin]').click()");await pg.wait_for_timeout(300)
        R["noktaya dokununca kart"]=await pg.evaluate(f"U.mapSel==='{pid}'&&document.querySelector('#app').innerText.includes(S.customers.get('{pid}').name)")
        await pg.click("[data-act=zme]");await pg.wait_for_timeout(500)
        R["konumuma git"]=await pg.evaluate("!!document.querySelector('#mapSvg .me')")
        R["yatay taşma yok"]=await pg.evaluate("document.documentElement.scrollWidth")<=W
        await pg.evaluate("U.tab='yakin';render()");await pg.click("#app [data-act=findPros]");await pg.wait_for_timeout(800)
        R["yakındakilerde trafik"]=await pg.evaluate("[...document.querySelectorAll('#sheet a')].some(a=>a.href.includes('layer=traffic'))")
        await b.close()
        print(W,json.dumps(R,ensure_ascii=False))
        return [f"{W}:{k}" for k,v in R.items() if not v],errs
async def main():
    bad=[];er=[]
    for W in (390,320):
        x,y=await run(W);bad+=x;er+=y
    print("HATALAR",bad);print("JS HATALARI:",er)
asyncio.run(main())
