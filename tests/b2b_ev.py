# Otokoç / Opar B2B kısayolları (kod kopyala + siteyi aç) ve ev konumunun öğrenilmesi ("Şu an evdeyim", tek akşamda öneri, eve varınca rapor hatırlatması).
import os
import asyncio,json
from playwright.async_api import async_playwright
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"qa.py")).read().split("TABS=")[0])
HOME={"latitude":41.0300,"longitude":29.2500}   # varsayılan Sancaktepe noktasından ~3 km uzakta
async def run(W):
    async with async_playwright() as p:
        b=await p.chromium.launch()
        ctx=await b.new_context(viewport={"width":W,"height":850},geolocation=HOME,permissions=["geolocation","clipboard-read","clipboard-write"])
        await setup(ctx)
        await ctx.add_init_script("document.addEventListener('click',e=>{const a=e.target.closest('a[href]');if(a&&!/^https?:\\/\\/127/.test(a.href))e.preventDefault()},true);window.open=()=>null;")
        pg=await ctx.new_page();errs=[];pg.on("pageerror",lambda e:errs.append(str(e)[:160]))
        await pg.clock.set_fixed_time("2026-11-24T19:30:00")  # Salı akşamı
        await pg.goto("http://127.0.0.1:8767/boot.html");await pg.wait_for_timeout(1500)
        await pg.click("[data-act=sample]");await pg.wait_for_timeout(300)
        R={}
        # ---- B2B ----
        await pg.evaluate("U.tab='stok';U.stk.q='';U.stk.detail=null;render()");await pg.wait_for_timeout(100)
        R["boş aramada B2B satırı yok"]=await pg.evaluate("!document.querySelector('.b2b')")
        await pg.evaluate("U.stk.q='1K0615301';render()");await pg.wait_for_timeout(100)
        hrefs=await pg.evaluate("[...document.querySelectorAll('a[data-b2b]')].map(a=>a.href+'|'+a.dataset.code)")
        R["stok aramasında iki B2B düğmesi"]=len(hrefs)==2 and "b2b.otokocyedekparca.com.tr/web/login|1K0615301" in hrefs[0] and "b2bopar.tofas.com.tr/Login|1K0615301" in hrefs[1]
        await pg.click("a[data-b2b=opar]");await pg.wait_for_timeout(300)
        R["kod panoya kopyalandı"]=await pg.evaluate("navigator.clipboard.readText()")=="1K0615301"
        R["kullanıcıya söylendi"]="kopyalandı" in await pg.evaluate("document.querySelector('#toast').textContent")
        pid=await pg.evaluate("(()=>{const p=products().find(p=>p.oem)||products()[0];return p&&p.id})()")
        R["örnek veride ürün var"]=bool(pid)
        if pid:
            await pg.evaluate(f"U.stk.q='';U.stk.detail='{pid}';render()");await pg.wait_for_timeout(100)
            code=await pg.evaluate(f"(()=>{{const p=S.products.get('{pid}');return p.oem||p.sku||p.name}})()")
            R["ürün detayında B2B (OEM ile)"]=await pg.evaluate("[...document.querySelectorAll('a[data-b2b]')].map(a=>a.dataset.code)")==[code,code]
            await pg.evaluate("U.stk.detail=null")
        await pg.evaluate("U.cart={cid:custList()[0].id,lines:[],q:'55702853',disc:'',note:''};U.tab='satis';U.detail=null;render()");await pg.wait_for_timeout(150)
        R["sepette B2B düğmeleri"]=await pg.evaluate("document.querySelectorAll('a[data-b2b][data-code=\"55702853\"]').length")==2
        R[f"yatay taşma yok (sepet)"]=await pg.evaluate("document.documentElement.scrollWidth")<=W
        # adres ayarı
        await pg.evaluate("U.tab='rota';U.dayOpen=true;render()");await pg.wait_for_timeout(100)
        R["ayarda varsayılan Otokoç adresi"]=await pg.evaluate("document.querySelector('#df_b2b1').value")=="https://b2b.otokocyedekparca.com.tr/web/login"
        await pg.fill("#df_b2b2","b2bopar.tofas.com.tr/Yeni");await pg.fill("#df_b2b1","javascript:alert(1)");await pg.click("#dayForm button[type=submit]");await pg.wait_for_timeout(300)
        R["yeni adres https ile kaydedildi"]=await pg.evaluate("b2bSites()[1].url")=="https://b2bopar.tofas.com.tr/Yeni"
        R["geçersiz adres varsayılana döner"]=await pg.evaluate("b2bSites()[0].url")=="https://b2b.otokocyedekparca.com.tr/web/login"
        # ---- Ev konumu ----
        await pg.evaluate("saveDay({homeLat:DAY_DEF.homeLat,homeLng:DAY_DEF.homeLng,homeOk:false});localStorage.removeItem(GK);U.homeSuggest=null;U.dayOpen=false;U.tab='rota';render()");await pg.wait_for_timeout(200)
        R["doğrulanmamış ev uyarısı"]=await pg.evaluate("!!document.querySelector('#homeUnsure')")
        # tek akşamlık konumdan öneri (doğrulanmamış evde)
        await pg.evaluate("localStorage.removeItem(GK);U.homeSuggest=null;learnHome({lat:41.03,lng:29.25,acc:40})")
        R["tek akşamda ev önerisi"]=await pg.evaluate("!!U.homeSuggest&&Math.abs(U.homeSuggest.lat-41.03)<1e-6")
        await pg.evaluate("U.homeSuggest=null;render()");await pg.wait_for_timeout(100)
        await pg.click("#homeUnsure [data-act=homeHere]");await pg.wait_for_timeout(900)
        R["Şu an evdeyim kaydetti"]=await pg.evaluate("day().homeOk===true&&Math.abs(day().homeLat-41.03)<1e-6&&Math.abs(day().homeLng-29.25)<1e-6")
        R["uyarı kalktı"]=await pg.evaluate("!document.querySelector('#homeUnsure')")
        await pg.click("#toast button");await pg.wait_for_timeout(400)
        R["geri al çalışıyor"]=await pg.evaluate("day().homeLat===DAY_DEF.homeLat&&!day().homeOk")
        await pg.evaluate("saveDay({homeLat:41.03,homeLng:29.25,homeOk:true})");await pg.wait_for_timeout(200)
        R["doğrulanmış evde tek akşam öneri yok"]=await pg.evaluate("localStorage.removeItem(GK);U.homeSuggest=null;learnHome({lat:41.10,lng:29.30,acc:40});!U.homeSuggest")
        # uzaktayken eve dönüş kartında "Şu an evdeyim"
        await pg.clock.set_fixed_time("2026-11-24T17:20:00")
        await pg.evaluate("U.lastPos={lat:41.00,lng:28.90,acc:20,t:Date.now()};U.tab='rota';render()");await pg.wait_for_timeout(150)
        R["eve dönüş kartında Şu an evdeyim"]=await pg.evaluate("!!document.querySelector('.hero [data-act=homeHere]')")
        # eve varınca rapor hatırlatması
        cid=await pg.evaluate("custList()[0].id")
        await pg.evaluate(f"U.tab='ziyaret';U.visitFor='{cid}';render()");await pg.wait_for_timeout(200)
        await pg.select_option("#vf_res","Bilgi / tanıtım");await pg.click("#visitForm button[type=submit]");await pg.wait_for_timeout(400)
        await pg.evaluate("U.lastPos={lat:41.0301,lng:29.2501,acc:20,t:Date.now()};U.visitFor=null;U.tab='rota';render()");await pg.wait_for_timeout(150)
        R["eve varınca kart"]=await pg.evaluate("!!document.querySelector('#homeArrived')&&!document.querySelector('.hero [data-act=homeHere]')")
        await pg.click("#homeArrived [data-act=homeReport]");await pg.wait_for_timeout(200)
        R["gün sonu ekranına gitti"]=await pg.evaluate("U.tab==='gunsonu'")
        await pg.evaluate("U.tab='rota';render()")
        R["bugün tekrar gösterilmiyor"]=await pg.evaluate("!document.querySelector('#homeArrived')")
        R["yatay taşma yok (rota)"]=await pg.evaluate("document.documentElement.scrollWidth")<=W
        await b.close()
        print(W,json.dumps(R,ensure_ascii=False))
        return [f"{W}:{k}" for k,v in R.items() if v is False],errs
async def main():
    bad=[];er=[]
    for W in (390,320):
        x,y=await run(W);bad+=x;er+=y
    print("HATALAR",bad);print("JS HATALARI:",er)
asyncio.run(main())
