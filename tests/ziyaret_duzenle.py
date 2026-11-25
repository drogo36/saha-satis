# Ziyaret düzenleme (Ziyaretler listesinde "Düzenle") ve ziyaret başlarken konumun kendiliğinden alınması (ziyarete, konumsuz müşteriye ve gün sonu "Gidilen yerler"e).
import os
import asyncio,json
from playwright.async_api import async_playwright
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"qa.py")).read().split("TABS=")[0])
HERE={"latitude":41.0050,"longitude":28.9500}
async def run(W):
    async with async_playwright() as p:
        b=await p.chromium.launch()
        ctx=await b.new_context(viewport={"width":W,"height":850},geolocation=HERE,permissions=["geolocation"])
        await setup(ctx)
        await ctx.add_init_script("document.addEventListener('click',e=>{const a=e.target.closest('a[href]');if(a&&!/^https?:\\/\\/127/.test(a.href))e.preventDefault()},true);window.open=()=>null;")
        pg=await ctx.new_page();errs=[];pg.on("pageerror",lambda e:errs.append(str(e)[:160]))
        await pg.clock.set_fixed_time("2026-11-25T11:00:00")  # Çarşamba
        await pg.goto("http://127.0.0.1:8767/boot.html");await pg.wait_for_timeout(1500)
        await pg.click("[data-act=sample]");await pg.wait_for_timeout(300)
        await pg.evaluate("U.arrFixMs=100")  # tarayıcı öykünmesinde anlık konum beklemesi kısaltılır; telefonda 8 sn
        R={}
        # ---- düzenleme ----
        await pg.evaluate("U.tab='ziyaret';U.detail=null;U.visitFor=null;render()");await pg.wait_for_timeout(150)
        n0=await pg.evaluate("S.visits.size")
        R["örnek veride ziyaret var"]=n0>0
        R["listede Düzenle düğmesi"]=await pg.evaluate("document.querySelectorAll('[data-act=editVisit]').length")>0
        vid=await pg.evaluate("document.querySelector('[data-act=editVisit]').dataset.id")
        old=await pg.evaluate(f"JSON.parse(JSON.stringify(S.visits.get('{vid}')))")
        await pg.click("[data-act=editVisit] >> nth=0");await pg.wait_for_timeout(200)
        R["düzenleme formu açıldı"]="Ziyareti düzenle" in await pg.evaluate("document.querySelector('#visitForm').closest('section').innerText")
        R["eski değerler dolu"]=await pg.evaluate("document.querySelector('#vf_date').value")==old["date"] and await pg.evaluate("document.querySelector('#vf_note').value")==(old.get("note") or "") and await pg.evaluate("document.querySelector('#vf_res').value")==old["result"]
        await pg.fill("#vf_note","Düzeltilmiş not: 20 adet balata istedi");await pg.select_option("#vf_res","Teklif verildi");await pg.fill("#vf_amt","1500")
        await pg.click("#visitForm button[type=submit]");await pg.wait_for_timeout(400)
        v=await pg.evaluate(f"JSON.parse(JSON.stringify(S.visits.get('{vid}')))")
        R["aynı kayıt güncellendi (yeni kayıt yok)"]=await pg.evaluate("S.visits.size")==n0 and v["note"].startswith("Düzeltilmiş") and v["result"]=="Teklif verildi" and v["amount"]==1500
        R["müşteri ve tarih korunuyor"]=v["customerId"]==old["customerId"] and v["date"]==old["date"]
        R["listeye dönüldü"]=await pg.evaluate("!document.querySelector('#visitForm')&&document.body.innerText.includes('Düzeltilmiş not')")
        await pg.click("#toast button");await pg.wait_for_timeout(400)
        R["geri al eski hale döndürdü"]=await pg.evaluate(f"S.visits.get('{vid}').note")==(old.get("note") or "")
        # müşteri kartından da düzenlenebiliyor
        await pg.evaluate(f"U.tab='musteri';U.detail=S.visits.get('{vid}').customerId;render()");await pg.wait_for_timeout(150)
        if await pg.evaluate("!!document.querySelector('[data-act=editVisit]')"):
            await pg.click("[data-act=editVisit] >> nth=0");await pg.wait_for_timeout(200)
            R["müşteri kartından düzenle açılıyor"]=await pg.evaluate("U.tab==='ziyaret'&&!!document.querySelector('#visitForm[data-vid]:not([data-vid=\"\"])')")
            await pg.click("[data-act=cancelVisit]");await pg.wait_for_timeout(150)
        # ---- ziyaret başlarken konum ----
        await pg.evaluate("save({id:'cNoGeo',kind:'customer',name:'Konumsuz Oto Parça',status:'Aday',tier:'B',freq:14,region:'Bayrampaşa',city:'İstanbul',createdAt:Date.now()})");await pg.wait_for_timeout(200)
        await pg.evaluate("U.tab='ziyaret';U.visitFor=null;U.visitEdit=null;render()");await pg.wait_for_timeout(150)
        await pg.select_option("#pickVisit","cNoGeo");await pg.wait_for_timeout(1200)
        R["formda konum alındı yazıyor"]="Konum alındı" in await pg.evaluate("(document.querySelector('#vfGeo')||{}).textContent||''")
        R["konumsuz müşteriye konum kaydedildi"]=await pg.evaluate("(c=>c&&Math.abs(c.lat-41.005)<1e-5&&Math.abs(c.lng-28.95)<1e-5)(S.customers.get('cNoGeo'))")
        await pg.select_option("#vf_res","Bilgi / tanıtım");await pg.click("#visitForm button[type=submit]");await pg.wait_for_timeout(400)
        R["ziyarete konum yazıldı"]=await pg.evaluate("[...S.visits.values()].some(v=>v.customerId==='cNoGeo'&&Math.abs(v.lat-41.005)<1e-5&&typeof v.acc==='number')")
        # konumu olan müşteride ziyareti başlat: müşteri konumu değişmez, ziyaret konumu alınır
        cid=await pg.evaluate("custList().find(c=>hasGeo(c)&&c.id!=='cNoGeo').id")
        before=await pg.evaluate(f"[S.customers.get('{cid}').lat,S.customers.get('{cid}').lng]")
        await pg.evaluate(f"(()=>{{const x=document.createElement('button');x.dataset.act='startLive';x.dataset.id='{cid}';x.id='tmpStart';document.body.appendChild(x)}})()")
        await pg.evaluate("document.getElementById('tmpStart').click()");await pg.wait_for_timeout(1200)
        R["Başla deyince konum alındı"]=await pg.evaluate("!!U.live&&Math.abs(U.live.lat-41.005)<1e-5")
        R["kayıtlı müşteri konumu değişmedi"]=await pg.evaluate(f"[S.customers.get('{cid}').lat,S.customers.get('{cid}').lng]")==before
        await pg.evaluate(f"U.tab='ziyaret';U.visitFor='{cid}';U.visitEdit=null;render()");await pg.wait_for_timeout(200)
        await pg.select_option("#vf_res","Bilgi / tanıtım");await pg.click("#visitForm button[type=submit]");await pg.wait_for_timeout(400)
        R["canlı ziyaretin konumu kayda geçti"]=await pg.evaluate(f"[...S.visits.values()].some(v=>v.customerId==='{cid}'&&v.date===today()&&Math.abs(v.lat-41.005)<1e-5)")
        # gün sonu: gidilen yerler
        await pg.evaluate("U.tab='gunsonu';U.repDate=null;render()");await pg.wait_for_timeout(200)
        txt=await pg.evaluate("(document.querySelector('#goneList')||{}).innerText||''")
        R["gün sonunda gidilen yerler"]="Konumsuz Oto Parça" in txt and "ziyaret konumu" in txt
        href=await pg.evaluate("(document.querySelector('#goneMap')||{}).href||''")
        R["gidilen yol haritada"]="google.com/maps/dir" in href and "41.005%2C28.95" in href
        R["yol hesabında ziyaret konumu"]=await pg.evaluate("dayReport(today()).pts.some(p=>Math.abs(p.lat-41.005)<1e-5)")
        R["yatay taşma yok (gün sonu)"]=await pg.evaluate("document.documentElement.scrollWidth")<=W
        await pg.evaluate("U.tab='ziyaret';U.visitFor=null;render()");await pg.wait_for_timeout(100)
        R["yatay taşma yok (ziyaretler)"]=await pg.evaluate("document.documentElement.scrollWidth")<=W
        await b.close()
        print(W,json.dumps(R,ensure_ascii=False))
        return [f"{W}:{k}" for k,v in R.items() if v is False],errs
async def main():
    bad=[];er=[]
    for W in (390,320):
        x,y=await run(W);bad+=x;er+=y
    print("HATALAR",bad);print("JS HATALARI:",er)
asyncio.run(main())
