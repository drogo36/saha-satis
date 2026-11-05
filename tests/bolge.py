# Haritada ısı görünümü ve alan çizerek seçim; ziyaret formuna kullanıcının eklediği alanlar.
import os
import asyncio,json
from playwright.async_api import async_playwright
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"qa.py")).read().split("TABS=")[0])
PNG=bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360f8cf000000020001e221bc330000000049454e44ae426082")
async def run(W):
    async with async_playwright() as p:
        b=await p.chromium.launch()
        ctx=await b.new_context(timezone_id="Europe/Istanbul",viewport={"width":W,"height":900},geolocation={"latitude":39.5,"longitude":32.5},permissions=["geolocation"])
        await setup(ctx)
        await ctx.route("https://tile.openstreetmap.org/**",lambda r:r.fulfill(status=200,headers=H,content_type="image/png",body=PNG))
        pg=await ctx.new_page();errs=[];pg.on("pageerror",lambda e:errs.append(str(e)[:160]))
        await pg.goto("http://127.0.0.1:8767/boot.html");await pg.wait_for_timeout(1500)
        await pg.click("[data-act=sample]");await pg.wait_for_timeout(300)
        ev=pg.evaluate;wait=pg.wait_for_timeout;R={}
        await ev("U.selected=new Set();keepUI();U.tab='harita';U.detail=null;render()");await wait(300)
        count="document.querySelectorAll('#mapSvg circle.heat').length"
        R["ısı başta kapalı"]=await ev(count)==0
        for k in ("potansiyel","ziyaret","ciro"):
            await pg.click(f"[data-act=mapHeat][data-v={k}]");await wait(150)
            n=await ev(count);exp=await ev("(k)=>mapPoints().filter(c=>heatVal(c,k)>0).length",k)
            R[f"ısı {k}"]=await ev("(k)=>U.mapHeat===k",k) and (n>0 or exp==0)
        R["ısı açıkken noktalar duruyor"]=await ev("document.querySelectorAll('#mapSvg [data-pin]').length===mapPoints().length")
        # kayıt yokken çökme olmaz
        await ev("(()=>{const s=heatVal;U.mapHeat='ciro';render()})()")
        await pg.click("[data-act=mapHeat][data-v='']");await wait(150);R["ısı kapandı"]=await ev(count)==0
        # alan çiz: bir noktanın çevresini çiz
        await pg.click("[data-act=mapLasso]");await wait(150)
        R["çizim modu"]=await ev("U.lasso&&document.querySelector('#mapSvg').classList.contains('lasso')")
        P=await ev("[...document.querySelectorAll('#mapSvg [data-pin]')].map(e=>{const r=e.getBoundingClientRect();return {id:e.dataset.pin,x:r.x+r.width/2,y:r.y+r.height/2}})")
        bb=await pg.locator("#mapSvg").bounding_box()
        inside=[q for q in P if bb["x"]+25<q["x"]<bb["x"]+bb["width"]-25 and bb["y"]+25<q["y"]<bb["y"]+bb["height"]-25]
        target=inside[0];sz=14
        await pg.evaluate("window.scrollTo(0,0)");await wait(50)
        bb=await pg.locator("#mapSvg").bounding_box();P2=await ev("(id)=>{const e=document.querySelector(`#mapSvg [data-pin='${id}']`).getBoundingClientRect();return {x:e.x+e.width/2,y:e.y+e.height/2}}",target["id"])
        x,y=P2["x"],P2["y"]
        c0=await ev("[M.cx,M.cy]")
        await pg.mouse.move(x-sz,y-sz);await pg.mouse.down()
        for dx,dy in ((sz,-sz),(sz,sz),(-sz,sz),(-sz,-sz)):
            await pg.mouse.move(x+dx,y+dy,steps=4)
        await pg.mouse.up();await wait(250)
        sel=await ev("U.lassoSel")
        R["çizilen alandaki müşteri seçildi"]=bool(sel) and target["id"] in sel
        R["uzak müşteri seçilmedi"]=bool(sel) and len(sel)<len(P)
        R["çizerken harita kaymadı"]=await ev("[M.cx,M.cy]")==c0
        R["çizim modu kapandı, panel açıldı"]=await ev("!U.lasso&&!!document.querySelector('#lassoPanel')")
        R["seçilenler vurgulu"]=await ev("document.querySelectorAll('#mapSvg .pin.las').length")>=1
        R["taşma yok (harita)"]=await ev("document.documentElement.scrollWidth")<=W
        await wait(100);await pg.click("#lassoPanel [data-act=lassoAdd]");await wait(200)
        R["rotaya eklendi"]=await ev("(a)=>a.every(i=>U.selected.has(i))&&!U.lassoSel",sel)
        # çizim sonrası harita eski gibi sürüklenir
        await pg.locator("#mapSvg").scroll_into_view_if_needed();await wait(100);bb=await pg.locator("#mapSvg").bounding_box()  # panel kapanınca harita yer değiştirir
        c1=await ev("[M.cx,M.cy]");await pg.mouse.move(bb["x"]+60,bb["y"]+60);await pg.mouse.down();await pg.mouse.move(bb["x"]+120,bb["y"]+100,steps=5);await pg.mouse.up();await wait(200)
        R["harita sürüklenmeye devam ediyor"]=await ev("[M.cx,M.cy]")!=c1
        # küçük dokunma alan sayılmaz
        await ev("U.lasso=true;render()");await wait(100);await pg.locator("#mapSvg").scroll_into_view_if_needed();bb=await pg.locator("#mapSvg").bounding_box();await pg.mouse.move(bb["x"]+80,bb["y"]+80);await pg.mouse.down();await pg.mouse.up();await wait(200)
        R["dokunma alan sayılmıyor"]=await ev("!U.lasso&&!U.lassoSel")
        # ziyaret formu alanları
        await ev("U.tab='rapor';render()");await wait(200)
        await pg.fill("#vfld_label","Rakip marka");await pg.click("#vfldForm button[type=submit]");await wait(200)
        await pg.fill("#vfld_label","Rakip marka");await pg.click("#vfldForm button[type=submit]");await wait(150)
        R["aynı alan iki kez eklenmiyor"]=await ev("vFields().length")==1
        await pg.fill("#vfld_label","<b>Raf</b>");await pg.click("#vfldForm button[type=submit]");await wait(200)
        cid=await ev("custList()[0].id")
        await ev("(id)=>{U.tab='ziyaret';U.visitFor=id;render()}",cid);await wait(150)
        R["formda alan görünüyor"]=await ev("!!document.querySelector('#vf_x0')&&document.querySelector('#visitForm').textContent.includes('Rakip marka')")
        R["alan adı güvenli gösteriliyor"]=await ev("!document.querySelector('#visitForm b')||![...document.querySelectorAll('#visitForm b')].some(e=>e.textContent==='Raf')")
        await pg.fill("#vf_x0","Bosch");await pg.click("#visitForm button[type=submit]");await wait(300)
        R["değer kaydedildi"]=await ev("[...S.visits.values()].some(v=>v.extra&&v.extra['Rakip marka']==='Bosch'&&!('<b>Raf</b>' in v.extra))")
        await ev("U.tab='ziyaret';U.visitFor=null;render()");await wait(150)
        R["listede görünüyor"]="Rakip marka: Bosch" in await ev("document.querySelector('#app').innerText")
        await ev("U.tab='rapor';render()");await wait(150)
        await pg.click("[data-act=delVfld] >> nth=0");await wait(200)
        R["alan kaldırıldı"]=await ev("vFields().length")==1
        R["eski veri duruyor"]=await ev("[...S.visits.values()].some(v=>v.extra&&v.extra['Rakip marka']==='Bosch')")
        await pg.click("#toast button");await wait(200);R["geri alındı"]=await ev("vFields().includes('Rakip marka')")
        R["eski ziyarette alan yok, sorun yok"]=await ev("(()=>{render();return true})()")
        R["taşma yok"]=await ev("document.documentElement.scrollWidth")<=W
        await b.close();print(W,json.dumps(R,ensure_ascii=False))
        return [f"{W}:{k}" for k,v in R.items() if v is False],errs
async def main():
    bad=[];er=[]
    for W in (390,320):
        x,y=await run(W);bad+=x;er+=y
    print("HATALAR",bad);print("JS HATALARI:",er)
asyncio.run(main())
