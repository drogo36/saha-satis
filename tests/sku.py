import os
import asyncio,json
from playwright.async_api import async_playwright
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"qa.py")).read().split("TABS=")[0])
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch();R={}
        for W in [1024,390]:
            ctx=await b.new_context(viewport={"width":W,"height":800});await setup(ctx);pg=await ctx.new_page();errs=[];pg.on("pageerror",lambda e:errs.append(str(e)[:150]))
            await pg.goto("http://127.0.0.1:8767/boot.html");await pg.wait_for_timeout(1500)
            await pg.evaluate("U.tab='rota';render()");await pg.click("[data-act=sample]");await pg.wait_for_timeout(300)
            await pg.evaluate("U.tab='stok';render();window.scrollTo(0,0)");await pg.wait_for_timeout(200)
            if W==1024:
                R["sütunlar"]=await pg.evaluate("[...document.querySelectorAll('#app thead th')].map(t=>t.textContent).join(' | ')")
                R["ilk satır"]=await pg.evaluate("[...document.querySelector('#app tbody tr').children].map(t=>t.innerText.trim()).slice(0,6).join(' | ')")
                await pg.fill("#stkQ","db 2040");await pg.wait_for_timeout(500);R["stok koduyla arama"]=await pg.evaluate("[...document.querySelectorAll('#app tbody tr td:nth-child(2)')].map(t=>t.textContent).join(',')")
                await pg.fill("#stkQ","");await pg.wait_for_timeout(400)
                R["metinde stok kodu tanıma"]=await pg.evaluate("findCodes('müşteri FR 1001 den 5 tane, yf-0307 de lazım').hits.map(h=>h.p.sku).join(',')")
                await pg.click("[data-act=stkNew]");await pg.fill("#p2_sku","fr-1001");await pg.fill("#p2_name","Kopya");await pg.click("#prodForm2 button[type=submit]");await pg.wait_for_timeout(300)
                R["aynı stok kodu engeli"]=await pg.evaluate("!products().some(p=>p.name==='Kopya')")
                # Excel içe aktarma (sütun eşleme + kayıt)
                await pg.evaluate("""(async()=>{U.import={kind:'product',file:'stok.xlsx',headers:['Stok Kodu','Malzeme Adı','Orijinal No','Fiyat','Miktar'],rows:[{'Stok Kodu':'FR-1001','Malzeme Adı':'Ön fren balatası (örnek)','Orijinal No':'1K0698151','Fiyat':'1.300,00','Miktar':'55'},{'Stok Kodu':'AM-5500','Malzeme Adı':'Amortisör','Orijinal No':'5208.N7','Fiyat':'2.450','Miktar':'8'}]};
                  U.import.map={};['sku','pname','oem','brand','price','stock'].forEach(k=>U.import.map[k]=guessCol(U.import.headers,k));window._map=JSON.stringify(U.import.map);await doImport()})()""");await pg.wait_for_timeout(400)
                R["Excel sütun eşleme"]=await pg.evaluate("window._map")
                R["Excel sonrası"]=await pg.evaluate("products().filter(p=>['FR-1001','AM-5500'].includes(p.sku)).map(p=>p.sku+':'+p.name+':'+p.price+':'+p.stock).join(' ; ')+' | toplam '+S.products.size")
                await pg.screenshot(path=os.path.join(os.environ.get("TEST_OUT","/tmp"),"sku-wide.png"))
            else:
                R["telefon görünümü"]=await pg.evaluate("[...document.querySelector('#app tbody tr').children].slice(0,3).map(td=>td.getAttribute('data-l')+': '+td.innerText.trim()).join(' | ')")
                R["telefon taşma"]=await pg.evaluate("document.documentElement.scrollWidth")
                await pg.screenshot(path=os.path.join(os.environ.get("TEST_OUT","/tmp"),"sku-phone.png"))
            R["hata "+str(W)]=errs;await ctx.close()
        print(json.dumps(R,ensure_ascii=False,indent=1));await b.close()
asyncio.run(main())
