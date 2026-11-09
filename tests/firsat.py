# Bugün sayfası: öğle/TokenFlex kartı gün boyu açık; arama tüm alanlarda (not, telefon, adres, parça) çalışır;
# üstteki 🔍 arama ziyaret notlarını da bulur; "Satış fırsatları" (hedef, açık teklif, alımı kesilen); Asistan yazma kutusu alt menünün altında kalmaz.
import os
import asyncio,json
from playwright.async_api import async_playwright
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"qa.py")).read().split("TABS=")[0])
ADD="""(()=>{const c={id:'c_tst',kind:'customer',name:'Deneme Parçacı',phone:'0532 111 22 33',address:'Gizemli Sokak No 7',notes:'rakip fiyatı zümrüt',status:'Aktif',tier:'B'};
const c2={id:'c_tst2',kind:'customer',name:'Kesik Alıcı',phone:'0533 444 55 66',status:'Aktif',tier:'A'};
saveMany([c,c2,
 {id:'v_tst',kind:'visit',customerId:'c_tst',date:'2026-11-01',result:'Teklif verildi',amount:9555555,parts:'XK9 kampana',note:'kehribar indirim istedi'},
 {id:'o_t1',kind:'order',type:'sipariş',customer:'Kesik Alıcı',customerId:'c_tst2',date:'2026-07-01',amount:5000000,no:'A1'},
 {id:'o_t2',kind:'order',type:'sipariş',customer:'Kesik Alıcı',customerId:'c_tst2',date:'2026-08-15',amount:6000000,no:'A2'}])})()"""
async def run(W):
    async with async_playwright() as p:
        b=await p.chromium.launch()
        ctx=await b.new_context(viewport={"width":W,"height":800},geolocation={"latitude":41.0186,"longitude":28.9078},permissions=["geolocation"])
        await setup(ctx)
        pg=await ctx.new_page();errs=[];pg.on("pageerror",lambda e:errs.append(str(e)[:160]))
        await pg.clock.set_fixed_time("2026-11-04T09:30:00")
        await pg.goto("http://127.0.0.1:8767/boot.html");await pg.wait_for_timeout(1500)
        await pg.click("[data-act=sample]");await pg.wait_for_timeout(300)
        await pg.evaluate(ADD);await pg.evaluate("U.tab='rota';render()");await pg.wait_for_timeout(200)
        R={}
        R["öğle kartı sabah da görünüyor"]=await pg.evaluate("!!document.querySelector('#ogle') && !inLunchWindow()")
        R["öğle kartı akşam da görünüyor"]=await pg.evaluate("(()=>{const D=Date;window.Date=class extends D{constructor(...a){super(...(a.length?a:['2026-11-04T19:30:00']))}};const r=!!(render(),document.querySelector('#ogle'));window.Date=D;render();return r})()")
        async def pick(q):
            await pg.fill("#custQ",q);await pg.wait_for_timeout(400)
            return await pg.evaluate("[...document.querySelectorAll('#app label.check b')].map(x=>x.innerText)")
        for q,lab in [("zümrüt","not"),("0532 111","telefon"),("gizemli","adres"),("kehribar","ziyaret notu"),("XK9","parça"),("deneme zümrüt","iki kelime")]:
            R[f"Bugün araması {lab} ile buluyor"]=(await pick(q))==["Deneme Parçacı"]
        R["olmayan kelime boş sonuç + bilgi"]=(await pick("yokboylebirsey"))==[] and await pg.evaluate("document.querySelector('#app').innerText.includes('hiçbir kayıtta geçmiyor')")
        await pick("")
        # Müşteriler sekmesi de aynı aramayı kullanır
        await pg.evaluate("U.tab='musteri';U.custQ='kehribar';render()");await pg.wait_for_timeout(200)
        R["Müşteriler araması ziyaret notunda buluyor"]=await pg.evaluate("[...document.querySelectorAll('#app .item .t')].map(x=>x.innerText).join('|')")=="Deneme Parçacı"
        await pg.evaluate("U.custQ='';U.tab='rota';render()")
        # üstteki 🔍
        await pg.click("[data-act=openSearch]");await pg.fill("#sq","kehribar");await pg.wait_for_timeout(500)
        txt=await pg.evaluate("document.querySelector('#sheet').innerText")
        R["🔍 ziyaret notunu buluyor"]="zİyaret notlari" in txt.lower() or "ziyaret notları" in txt.lower() or "ZİYARET NOTLARI" in txt and "Deneme Parçacı" in txt
        await pg.fill("#sq","Gizemli");await pg.wait_for_timeout(500)
        R["🔍 adresle müşteri buluyor"]="Deneme Parçacı" in await pg.evaluate("document.querySelector('#sheet').innerText")
        await pg.evaluate("document.querySelector('#sheet [data-act=closeSheet]').click()");await pg.wait_for_timeout(200)
        # satış fırsatları
        f=lambda:pg.evaluate("(document.querySelector('#firsat')||{}).textContent||''")
        t=await f()
        R["fırsatlar paneli var"]=bool(t)
        R["açık teklif listede"]="Deneme Parçacı" in t and "9.555.555" in t
        R["alımı kesilen listede"]="Kesik Alıcı" in t and "Alımı kesilen" in t
        R["hedef yokken hedef gir düğmesi"]=await pg.evaluate("!!document.querySelector('#firsat [data-goto-tab=rapor]')")
        await pg.evaluate("save(Object.assign({},settings(),{target:99999999}))");await pg.wait_for_timeout(200)
        R["hedefe kalan günlük tutar"]="Hedefe" in await f() and "iş gününde" in await f()
        # sipariş gelince teklif listeden düşer
        await pg.evaluate("save({id:'o_t3',kind:'order',type:'sipariş',customer:'Deneme Parçacı',customerId:'c_tst',date:'2026-11-03',amount:5})");await pg.wait_for_timeout(200)
        R["sipariş gelen teklif düşüyor"]="Deneme Parçacı" not in await f()
        await pg.evaluate("document.querySelector('#firsat [data-act=addSel]').click()");await pg.wait_for_timeout(200)
        R["+ Rota çalışıyor"]=await pg.evaluate("U.selected.has('c_tst2')")
        # eski kayıtlar bozulmadı
        R["örnek kayıtlar duruyor"]=await pg.evaluate("custList().length>=10")
        # Asistan: yazma kutusu alt menünün üstünde
        await pg.evaluate("U.tab='asistan';render()");await pg.wait_for_timeout(200)
        R["asistan kutusu alt menünün üstünde"]=await pg.evaluate("(()=>{const f=document.querySelector('#chatForm').getBoundingClientRect(),n=document.querySelector('nav.bottom').getBoundingClientRect();return f.bottom<=n.top+1})()")
        R["asistan kutusu arka planlı"]=await pg.evaluate("getComputedStyle(document.querySelector('#chatForm')).backgroundColor!=='rgba(0, 0, 0, 0)'")
        for tab in ["rota","asistan","musteri"]:
            await pg.evaluate(f"U.tab='{tab}';render()");await pg.wait_for_timeout(150)
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
