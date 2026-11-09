# Tahsilat (kısmi ödeme), açık bakiye + hesap özeti, hedefe teklif katkısı, fotoğraflı yedek ve geri yükleme.
import os
import asyncio,json
from playwright.async_api import async_playwright
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"qa.py")).read().split("TABS=")[0])
ADD="""(()=>{saveMany([{id:'c_th',kind:'customer',name:'Tahsil Oto',contact:'Ali Bey',phone:'0532 222 33 44',status:'Aktif',tier:'B',term:30},
 {id:'o_f1',kind:'order',type:'fatura',customer:'Tahsil Oto',customerId:'c_th',date:'2026-09-01',amount:40000,no:'F-101'},
 {id:'o_f2',kind:'order',type:'fatura',customer:'Tahsil Oto',customerId:'c_th',date:'2026-10-20',amount:10000,no:'F-102'},
 {id:'o_f3',kind:'order',type:'fatura',customer:'Tahsil Oto',customerId:'c_th',date:'2026-08-01',amount:5000,no:'F-090',paid:true},
 {id:'v_th',kind:'visit',customerId:'c_th',date:'2026-11-02',result:'Teklif verildi',amount:300000,photos:['ph_test1']}])})()"""
async def run(W):
    async with async_playwright() as p:
        b=await p.chromium.launch()
        ctx=await b.new_context(viewport={"width":W,"height":800},geolocation={"latitude":41.0186,"longitude":28.9078},permissions=["geolocation"])
        await setup(ctx)
        pg=await ctx.new_page();errs=[];pg.on("pageerror",lambda e:errs.append(str(e)[:160]))
        await pg.clock.set_fixed_time("2026-11-09T10:00:00")
        await pg.goto("http://127.0.0.1:8767/boot.html");await pg.wait_for_timeout(1500)
        await pg.click("[data-act=sample]");await pg.wait_for_timeout(300)
        await pg.evaluate(ADD);await pg.wait_for_timeout(200)
        await pg.evaluate("photoPut('ph_test1','data:image/jpeg;base64,AAAA')")
        R={}
        R["eski kayıt (pays yok) kalan = tutar"]=await pg.evaluate("invLeft(S.orders.get('o_f1'))===40000 && invLeft(S.orders.get('o_f3'))===0")
        R["açık bakiye 50.000"]=await pg.evaluate("custBalance(S.customers.get('c_th'))===50000")
        await pg.evaluate("U.tab='musteri';U.detail='c_th';render()");await pg.wait_for_timeout(200)
        t=await pg.evaluate("(document.querySelector('#custBal')||{}).textContent||''")
        R["kartta açık bakiye görünüyor"]="50.000,00" in t and "2 fatura" in t
        # kısmi tahsilat
        await pg.evaluate("document.querySelector('[data-act=payOpen][data-id=o_f1]').click()");await pg.wait_for_timeout(300)
        R["tahsilat formu açıldı"]=await pg.evaluate("!!document.querySelector('#payForm')")
        await pg.fill("#pf_amt","15.000");await pg.select_option("#pf_met","Havale / EFT");await pg.click("#payForm button[type=submit]");await pg.wait_for_timeout(300)
        R["kalan 25.000"]=await pg.evaluate("invLeft(S.orders.get('o_f1'))===25000 && !S.orders.get('o_f1').paid")
        R["ödeme şekli kaydedildi"]=await pg.evaluate("S.orders.get('o_f1').pays[0].method==='Havale / EFT'")
        R["bakiye 35.000"]=await pg.evaluate("custBalance(S.customers.get('c_th'))===35000")
        R["geciken ödeme kalan tutarı kullanıyor"]=await pg.evaluate("(()=>{const g=overdueList().find(x=>x.c&&x.c.id==='c_th');return !!g&&g.total===25000})()")
        # hesap özeti
        await pg.evaluate("document.querySelector('[data-act=stmt]').click()");await pg.wait_for_timeout(200)
        m=await pg.evaluate("(document.querySelector('#msgTxt')||{}).value||''")
        R["hesap özeti metni"]="F-101" in m and "F-102" in m and "35.000,00" in m and "F-090" not in m and "Son ödemeniz" in m and "Ali Bey" in m
        R["hesap özeti WhatsApp düğmesi"]=await pg.evaluate("!!document.querySelector('a[href*=\"wa.me\"][href*=\"text=\"]')")
        # tam tahsilat faturayı kapatır, geri al geri getirir
        await pg.evaluate("U.payFor='o_f1';render()");await pg.fill("#pf_amt","25000");await pg.click("#payForm button[type=submit]");await pg.wait_for_timeout(300)
        R["tam tahsilat faturayı kapattı"]=await pg.evaluate("S.orders.get('o_f1').paid===true && invLeft(S.orders.get('o_f1'))===0")
        await pg.evaluate("document.querySelector('#toast button').click()");await pg.wait_for_timeout(300)
        R["geri al çalıştı"]=await pg.evaluate("!S.orders.get('o_f1').paid && invLeft(S.orders.get('o_f1'))===25000")
        # tahsilat silme
        await pg.evaluate("U.payFor='o_f1';render()");await pg.evaluate("document.querySelector('[data-act=payDel]').click()");await pg.wait_for_timeout(300)
        R["tahsilat silindi"]=await pg.evaluate("invLeft(S.orders.get('o_f1'))===40000")
        R["sipariş sekmesinde Tahsilat düğmesi"]=await pg.evaluate("U.payFor=null;U.tab='siparis';U.detail=null;render();!!document.querySelector('[data-act=payOpen]')")
        # hedef: teklif katkısı
        await pg.evaluate("save(Object.assign({},settings(),{target:99999999}))");await pg.evaluate("U.tab='rota';render()");await pg.wait_for_timeout(200)
        R["hedefe teklif katkısı yazıyor"]="Bekleyen" in await pg.evaluate("(document.querySelector('#oppCover')||{}).textContent||''")
        # fotoğraflı yedek
        dump=await pg.evaluate("""(async()=>{let got=null;const o=window.downloadBlob;window.downloadBlob=async(bl,fn)=>{got={t:await bl.text(),fn}};await backupNow(true);window.downloadBlob=o;return got})()""")
        j=json.loads(dump["t"])
        R["yedekte fotoğraf var"]=j.get("photos",{}).get("ph_test1")=="data:image/jpeg;base64,AAAA" and "fotolu" in dump["fn"]
        R["yedekte tahsilat alanları"]=any(d.get("id")=="o_f1" for d in j["data"])
        lite=await pg.evaluate("""(async()=>{let got=null;const o=window.downloadBlob;window.downloadBlob=async(bl,fn)=>{got=await bl.text()};await backupNow(false);window.downloadBlob=o;return got})()""")
        R["fotoğrafsız yedek"]="photos" not in json.loads(lite)
        await pg.evaluate("U.tab='rapor';render()");await pg.wait_for_timeout(200)
        R["rapor: fotoğrafsız yedek düğmesi"]=await pg.evaluate("!!document.querySelector('[data-act=backupLite]')")
        # geri yükleme fotoğrafı geri koyar
        await pg.evaluate("(async()=>{const db=await idb();await new Promise(r=>{const t=db.transaction('f','readwrite');t.objectStore('f').clear();t.oncomplete=r})})()");await pg.wait_for_timeout(200)
        await pg.evaluate("d=>restoreFrom(new File([d],'y.json'))",dump["t"]);await pg.wait_for_timeout(500)
        R["geri yükleme fotoğrafı getirdi"]=await pg.evaluate("photoGet('ph_test1')")=="data:image/jpeg;base64,AAAA"
        R["eski yedek (fotoğrafsız) hâlâ yükleniyor"]=await pg.evaluate("(async()=>{await restoreFrom(new File([JSON.stringify({app:'saha-satis',data:[{id:'c_old',kind:'customer',name:'Eski Yedek'}]})],'e.json'));return !!S.customers.get('c_old')})()")
        for tab,det in [("musteri","'c_th'"),("siparis","null"),("rapor","null")]:
            await pg.evaluate(f"U.tab='{tab}';U.detail={det};U.payFor='o_f2';render()");await pg.wait_for_timeout(150)
            R[f"yatay taşma yok ({tab})"]=await pg.evaluate("document.documentElement.scrollWidth")<=W
        await b.close()
        print(W,json.dumps(R,ensure_ascii=False))
        return [f"{W}:{k}" for k,v in R.items() if v is False],errs
async def main():
    bad=[];er=[]
    for W in (390,320):
        x,y=await run(W);bad+=x;er+=y
    print("HATALAR",bad);print("JS HATALARI:",er)
asyncio.run(main())
