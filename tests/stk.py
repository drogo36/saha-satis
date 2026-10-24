import os
import asyncio,json,base64
from playwright.async_api import async_playwright
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"qa.py")).read().split("TABS=")[0])
SENT={}
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch();ctx=await b.new_context(viewport={"width":390,"height":844});await setup(ctx)
        async def gem(route):
            body=json.loads(route.request.post_data);parts=body["contents"][-1]["parts"];SENT["parts"]=len(parts);SENT["img"]=any("inline_data" in x for x in parts);SENT["sys"]=body.get("systemInstruction",{}).get("parts",[{}])[0].get("text","")
            out='{"items":[{"code":"1K0 698 151","name":"Ön fren balatası","brand":"VW/Ford","qty":4},{"code":"0 986 494 123","name":"Fren balatası","brand":"Bosch","qty":2}]}' if SENT["img"] else "Stokta Ön fren balatası 40 adet."
            await route.fulfill(status=200,headers=H,content_type="application/json",body=json.dumps({"candidates":[{"content":{"parts":[{"text":out}]}}]}))
        await ctx.unroute("https://generativelanguage.googleapis.com/**");await ctx.route("https://generativelanguage.googleapis.com/**",gem)
        pg=await ctx.new_page();errs=[];pg.on("pageerror",lambda e:errs.append(str(e)[:150]))
        await pg.goto("http://127.0.0.1:8767/boot.html");await pg.wait_for_timeout(1500)
        await pg.evaluate("U.tab='rota';render()");await pg.click("[data-act=sample]");await pg.wait_for_timeout(300);await pg.evaluate("aiSave({key:'AIzaTEST'})")
        R={}
        R["kod tanıma"]=await pg.evaluate("(()=>{const r=findCodes('Müşteri 1k0.698.151 x10, 96823-45780 ve 1807185 istedi; ayrıca 7701208265 sordu');return r.hits.map(h=>h.p.oem).join(',')+' | bilinmeyen: '+r.unknown.join(',')})()")
        # ziyaret formunda canlı eşleşme
        await pg.evaluate("U.tab='ziyaret';U.visitFor=custList()[0].id;render()");await pg.fill("#vf_parts","1K0 698 151 x 10");await pg.wait_for_timeout(500)
        R["ziyaret formu çipi"]=await pg.inner_text("#vfCodes")
        # stok ekranı
        await pg.evaluate("U.tab='stok';U.visitFor=null;render()");await pg.wait_for_timeout(200)
        R["stok özeti"]=await pg.evaluate("document.querySelector('.hero').innerText.replace(/\\n/g,' / ')")
        await pg.fill("#stkQ","96823 45780");await pg.wait_for_timeout(500);R["OEM boşluklu arama"]=await pg.evaluate("[...document.querySelectorAll('#app .list>.item b')].map(x=>x.textContent).join(',')")
        await pg.fill("#stkQ","");await pg.wait_for_timeout(400)
        await pg.click("[data-act=stkAdj][data-d='1'] >> nth=0");await pg.wait_for_timeout(200);R["+1 stok"]=await pg.evaluate("products()[0].name+' '+products()[0].stock")
        await pg.click("[data-act=stkNew]");await pg.fill("#p2_name","Kopya");await pg.fill("#p2_oem","1807-185");await pg.click("#prodForm2 button[type=submit]");await pg.wait_for_timeout(300)
        R["tekrar OEM engeli"]=await pg.evaluate("!products().some(p=>p.name==='Kopya')")
        await pg.fill("#p2_oem","XYZ-999");await pg.fill("#p2_stock","2");await pg.fill("#p2_price","150");await pg.click("#prodForm2 button[type=submit]");await pg.wait_for_timeout(300)
        R["yeni ürün + kritik"]=await pg.evaluate("(p=>p&&p.stock+' adet kritik='+lowOf(p))(products().find(p=>p.name==='Kopya'))")
        # etiket fotoğrafı
        png=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
        await pg.set_input_files("#scanFile",files=[{"name":"etiket.png","mimeType":"image/png","buffer":png}]);await pg.wait_for_timeout(1500)
        R["etiket okuma"]=await pg.evaluate("U.stk.scan&&U.stk.scan.items?U.stk.scan.items.map(x=>x.code+'→'+(x.p?x.p.name:'yok')).join(' ; '):JSON.stringify(U.stk.scan)")
        R["görüntü gönderildi"]=SENT.get("img")
        await pg.click("[data-act=scanIn] >> nth=0");await pg.wait_for_timeout(300);R["stok girişi"]=await pg.evaluate("products().find(p=>p.oem==='1K0698151').stock")
        await pg.click("[data-act=scanNew] >> nth=0");await pg.wait_for_timeout(300);R["etiketten yeni ürün"]=await pg.evaluate("!!products().find(p=>p.oem==='0 986 494 123')")
        await pg.screenshot(path=os.path.join(os.environ.get("TEST_OUT","/tmp"),"stok.png"),full_page=False)
        # asistan bağlamı
        await pg.evaluate("U.tab='asistan';render()");await pg.evaluate("aiAsk('1K0698151 stokta var mı?')");await pg.wait_for_timeout(800)
        R["AI'ya stok gitti"]="STOK (" in SENT["sys"] and "SORUDA GEÇEN KODLAR" in SENT["sys"] and "KRİTİK STOK" in SENT["sys"]
        # sepet: serbest kalemde kod
        await pg.evaluate("U.cart={cid:custList()[0].id,lines:[],q:'',disc:'',note:''};U.tab='satis';render()")
        await pg.fill("#freeLine input[name=name]","9682345780");await pg.click("#freeLine button");await pg.wait_for_timeout(300)
        R["sepette kod→ürün"]=await pg.evaluate("U.cart.lines.map(l=>l.name+' '+l.price).join(',')")
        print(json.dumps(R,ensure_ascii=False,indent=1));print("HATALAR",errs)
        await b.close()
asyncio.run(main())
