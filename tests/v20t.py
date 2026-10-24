import os
import asyncio,json
from playwright.async_api import async_playwright
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"qa.py")).read().split("TABS=")[0])
MODE={"g":"act"}
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch();ctx=await b.new_context(viewport={"width":390,"height":844});await setup(ctx)
        async def gem(route):
            if MODE["g"]=="down": return await route.fulfill(status=503,headers=H,content_type="application/json",body=json.dumps({"error":{"message":"high demand"}}))
            body=json.loads(route.request.post_data);MODE["sys"]=body.get("systemInstruction",{}).get("parts",[{}])[0].get("text","")
            out='Tamam, aşağıdaki işlemleri onayına sunuyorum.\n<eylem>{"actions":[{"type":"delete_products","codes":["FR 1001","XX-404"]},{"type":"set_stock","code":"db-2040","stock":3},{"type":"add_route","customers":["Topkapı Ford Merkez (örnek)"]},{"type":"add_product","sku":"AM-77","name":"Amortisör ön","price":2400,"stock":6}]}</eylem>'
            await route.fulfill(status=200,headers=H,content_type="application/json",body=json.dumps({"candidates":[{"content":{"parts":[{"text":out}]}}]}))
        await ctx.unroute("https://generativelanguage.googleapis.com/**");await ctx.route("https://generativelanguage.googleapis.com/**",gem)
        pg=await ctx.new_page();errs=[];pg.on("pageerror",lambda e:errs.append(str(e)[:160]))
        await pg.goto("http://127.0.0.1:8767/boot.html");await pg.wait_for_timeout(1500)
        await pg.evaluate("U.tab='rota';render()");await pg.click("[data-act=sample]");await pg.wait_for_timeout(300);await pg.evaluate("aiSave({key:'AIzaTEST'})")
        R={};n=lambda:pg.evaluate("S.products.size")
        await pg.evaluate("U.tab='stok';render()")
        R["başlangıç"]=await n()
        # satırda sil (iki dokunuş) + geri al
        await pg.click("[data-act=stkDelOne] >> nth=0");await pg.click("[data-act=stkDelOne] >> nth=0");await pg.wait_for_timeout(300)
        R["satır sil"]=await n();R["geri al düğmesi"]=await pg.evaluate("!!document.querySelector('#toast button')")
        await pg.click("#toast button");await pg.wait_for_timeout(400);R["geri alındı"]=await n()
        # çoklu seçim
        await pg.click("[data-act=stkPick] >> nth=0");await pg.click("[data-act=stkPick] >> nth=1");await pg.wait_for_timeout(200)
        await pg.click("[data-act=stkDelSel]");await pg.wait_for_timeout(300);R["seçili 2 sil"]=await n()
        await pg.click("#toast button");await pg.wait_for_timeout(400);R["seçili geri"]=await n()
        # stoğu 0 olanlar
        await pg.evaluate("save(Object.assign({},products()[0],{stock:0}))");await pg.wait_for_timeout(200)
        await pg.click("[data-act=stkDelZero]");await pg.wait_for_timeout(300);R["0 stok sil"]=await n()
        await pg.click("#toast button");await pg.wait_for_timeout(400)
        # tümünü sil (SİL onayı)
        await pg.click("[data-act=stkDelAll]");await pg.fill("#delAllTxt","sil");await pg.click("#delAllForm button[type=submit]");await pg.wait_for_timeout(300);R["tümünü sil"]=await n()
        await pg.click("#toast button");await pg.wait_for_timeout(400);R["tüm geri"]=await n()
        # asistan işlemleri
        await pg.evaluate("U.tab='asistan';render()");await pg.evaluate("aiAsk(`FR 1001 i sil, DB 2040 stoğunu 3 yap, Topkapı Ford'u rotaya ekle, AM-77 amortisörü ekle`)");await pg.wait_for_timeout(900)
        R["önizleme"]=await pg.evaluate("[...document.querySelectorAll('#chatList .panel .why')].map(x=>x.innerText).join(' || ')")
        R["eylem bloğu gizli"]=await pg.evaluate("!document.querySelector('#chatList').innerText.includes('<eylem>')")
        R["asistana işlem yönergesi gitti"]="<eylem>" in MODE.get("sys","")
        await pg.click("[data-act=aiApply]");await pg.wait_for_timeout(500)
        R["uygulandı"]=await pg.evaluate("JSON.stringify({FR:!!products().find(p=>p.sku==='FR-1001'),DB:(products().find(p=>p.sku==='DB-2040')||{}).stock,AM:!!products().find(p=>p.sku==='AM-77'),rota:U.selected.has(custByName('Topkapı Ford Merkez (örnek)').id)})")
        # yapay zekâ çökünce yerel cevap
        MODE["g"]="down";await pg.evaluate("aiSave({key:'AIzaTEST'})")
        await pg.route("https://text.pollinations.ai/**",lambda r:r.abort());await pg.route("https://gen.pollinations.ai/**",lambda r:r.abort())
        await pg.evaluate("aiAsk('YF 0307 stokta var mı?')");await pg.wait_for_timeout(1500)
        R["yerel cevap"]=await pg.evaluate("U.chat[U.chat.length-1].text.slice(0,160)")
        # sipariş silinince stok iadesi + stoktan fazla uyarısı
        await pg.evaluate("U.cart={cid:custList()[0].id,lines:[],q:'',disc:'',note:''};U.tab='satis';render()")
        await pg.evaluate("(()=>{const p=products().find(p=>p.sku==='DB-2040');U.cart.lines.push({pid:p.id,name:p.name,sku:p.sku,price:6900,qty:5});render()})()")
        R["stoktan fazla uyarısı"]=await pg.evaluate("document.querySelector('#app').innerText.includes('stokta sadece 3 adet')")
        await pg.evaluate("(()=>{U.cart.lines[0].qty=2;render()})()");await pg.click("[data-act=cartSave]");await pg.wait_for_timeout(300)
        R["sipariş sonrası stok"]=await pg.evaluate("products().find(p=>p.sku==='DB-2040').stock")
        await pg.evaluate("U.tab='siparis';render()");oid=await pg.evaluate("[...S.orders.values()].find(o=>o.importedFrom==='uygulama').id")
        await pg.click(f"[data-act=delOrd][data-id={oid}]");await pg.click(f"[data-act=delOrd][data-id={oid}]");await pg.wait_for_timeout(400)
        R["sipariş silinince stok"]=await pg.evaluate("products().find(p=>p.sku==='DB-2040').stock")
        # örnek temizliği
        await pg.evaluate("save({id:'c_real',kind:'customer',name:'Gerçek Müşteri'})");await pg.evaluate("U.tab='rapor';render()")
        await pg.click("[data-act=clearSample]");await pg.wait_for_timeout(400)
        R["örnek temizliği"]=await pg.evaluate("JSON.stringify({müşteri:S.customers.size,ziyaret:S.visits.size,sipariş:S.orders.size,ürün:S.products.size,gerçekKaldı:S.customers.has('c_real')})")
        print(json.dumps(R,ensure_ascii=False,indent=1));print("HATALAR",errs)
        await b.close()
asyncio.run(main())
