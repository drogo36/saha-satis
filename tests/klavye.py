# Arama kutularında yazarken kutu yerinde kalmalı (telefonda klavye kapanmasın, harf kaybolmasın) ve sonuçlar süzülmeli.
import os
import asyncio,json
from playwright.async_api import async_playwright
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"qa.py")).read().split("TABS=")[0])
CASES=[("custQ","U.tab='musteri';U.detail=null;U.editCust=null;render()","Topkapı","document.querySelectorAll('#app [data-act=detail]').length"),
       ("ordQ","U.tab='siparis';U.detail=null;render()","Ford","document.querySelector('#app').innerText.length"),
       ("stkQ","U.tab='stok';U.detail=null;render()","fren","document.querySelector('#app').innerText.length"),
       ("cartQ","U.cart={cid:custList()[0].id,lines:[],q:'',disc:'',note:''};U.tab='satis';U.detail=null;render()","fren","document.querySelector('#app').innerText.length"),
       ("sq","U.tab='rota';render();document.querySelector('[data-act=openSearch]').click()","Topkapı","document.querySelector('#sheet').innerText.length"),
       ("pickQ","U.tab='rota';render();U.sheet='pickVisit';U._sheetFocused=false;U.pickQ='';renderSheet()","Topkapı","document.querySelectorAll('#sheet [data-act=pickVisitGo]').length")]
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        ctx=await b.new_context(viewport={"width":390,"height":844},has_touch=True,is_mobile=True)
        await setup(ctx)
        pg=await ctx.new_page();errs=[];pg.on("pageerror",lambda e:errs.append(str(e)[:160]))
        await pg.goto("http://127.0.0.1:8767/boot.html");await pg.wait_for_timeout(1500)
        await pg.click("[data-act=sample]");await pg.wait_for_timeout(300)
        R={};bad=[]
        for idv,js,txt,cnt in CASES:
            await pg.evaluate("U.sheet=null;renderSheet()");await pg.evaluate(js);await pg.wait_for_timeout(300)
            before=await pg.evaluate(cnt)
            await pg.click("#"+idv)
            await pg.evaluate(f"window._kutu=document.getElementById('{idv}');window._blur=0;window._kutu.addEventListener('blur',()=>window._blur++)")
            await pg.keyboard.type(txt,delay=260)   # her harften sonra ekran yeniden çizilir
            await pg.wait_for_timeout(450)
            r=await pg.evaluate(f"(()=>{{const el=document.getElementById('{idv}');return {{ayniKutu:el===window._kutu,odakta:document.activeElement===el,deger:el.value,blur:window._blur}}}})()")
            r["sonuç değişti"]=(await pg.evaluate(cnt))!=before
            R[idv]=r
            if not(r["ayniKutu"] and r["odakta"] and r["deger"]==txt and r["blur"]==0 and r["sonuç değişti"]): bad.append(idv)
            # Ara (Enter) klavyeyi kapatır
            await pg.keyboard.press("Enter");await pg.wait_for_timeout(100)
            if await pg.evaluate(f"document.activeElement===document.getElementById('{idv}')"): bad.append(idv+":enter")
        # başka sekmeye geçince kutudaki yazı yanlış kutuya taşınmamalı
        await pg.evaluate("U.sheet=null;renderSheet();U.tab='musteri';U.custQ='';U.ordQ='';render()");await pg.click("#custQ");await pg.keyboard.type("zz")
        await pg.evaluate("U.tab='siparis';render()");R["sekme değişince"]=await pg.evaluate("(document.getElementById('ordQ')||{}).value||''")
        if R["sekme değişince"]: bad.append("sekme")
        print(json.dumps(R,ensure_ascii=False))
        print("HATALAR",bad);print("JS HATALARI:",errs)
        await b.close()
asyncio.run(main())
