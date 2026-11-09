# Pazar çalışılmıyor (iş günü sayısı, sonraki ziyaret, ziyaret kaydı, bildirimler) ve "Ofise git" düğmesi + ofis adresi ayarı.
import os
import asyncio,json
from playwright.async_api import async_playwright
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"qa.py")).read().split("TABS=")[0])
async def run(W):
    async with async_playwright() as p:
        b=await p.chromium.launch()
        ctx=await b.new_context(viewport={"width":W,"height":800},geolocation={"latitude":41.0186,"longitude":28.9078},permissions=["geolocation"])
        await setup(ctx)
        pg=await ctx.new_page();errs=[];pg.on("pageerror",lambda e:errs.append(str(e)[:160]))
        await pg.clock.set_fixed_time("2026-11-09T10:00:00")  # Pazartesi
        await pg.goto("http://127.0.0.1:8767/boot.html");await pg.wait_for_timeout(1500)
        await pg.click("[data-act=sample]");await pg.wait_for_timeout(300)
        R={}
        R["Kasım'da kalan iş günü (Cumartesi dahil, Pazar hariç)"]=await pg.evaluate("workDaysLeft()")==19
        R["noSun Pazar->Pazartesi"]=await pg.evaluate("noSun('2026-11-15')==='2026-11-16' && noSun('2026-11-14')==='2026-11-14' && noSun('')===''")
        R["Pazartesi iş saatinde"]=await pg.evaluate("inWorkHours()")
        R["hafta içi Pazar notu yok"]=await pg.evaluate("U.tab='rota';render();!document.querySelector('#sunNote')")
        # ofis düğmesi
        href=await pg.evaluate("(document.querySelector('#officeRow #officeGo')||{}).href||''")
        R["Bugün sayfasında Ofise git"]="Siteler" in href and "Maltepe" in href
        R["eski ayarlarda da ofis varsayılan"]=await pg.evaluate("(async()=>{await saveDay({arriveBy:'18:00'});return day().office.includes('Siteler Yolu')})()")
        await pg.evaluate("U.tab='daha';render()");await pg.wait_for_timeout(100)
        R["Daha menüsünde Ofise git"]=await pg.evaluate("!!document.querySelector('#officeGo')")
        # ayardan ofis konumu
        await pg.evaluate("U.tab='rota';U.dayOpen=true;render()");await pg.fill("#df_ogeo","40.9420, 29.1200");await pg.click("#dayForm button[type=submit]");await pg.wait_for_timeout(300)
        R["ofis konumu kaydedildi"]=await pg.evaluate("day().officeLat===40.942&&day().officeLng===29.12")
        R["konumlu yol tarifi"]="40.942" in await pg.evaluate("document.querySelector('#officeGo').href")
        await pg.fill("#df_ogeo","");await pg.click("#dayForm button[type=submit]");await pg.wait_for_timeout(300)
        R["konum silinince adrese döner"]="Siteler" in await pg.evaluate("document.querySelector('#officeGo').href")
        # ziyaret: sonraki ziyaret Pazar seçilirse Pazartesi'ye kayar
        cid=await pg.evaluate("custList()[0].id")
        await pg.evaluate(f"U.tab='ziyaret';U.visitFor='{cid}';render()");await pg.wait_for_timeout(200)
        await pg.fill("#vf_next","2026-11-22");await pg.select_option("#vf_res","Bilgi / tanıtım");await pg.click("#visitForm button[type=submit]");await pg.wait_for_timeout(400)
        R["Pazar ziyareti Pazartesi'ye alındı"]=await pg.evaluate(f"S.customers.get('{cid}').nextVisit")=="2026-11-23"
        R["kullanıcıya söylendi"]="Pazartesi" in await pg.evaluate("document.querySelector('#toast').textContent")
        # varsayılan sonraki ziyaret Pazar olmaz (bugün+7 = Pazartesi, freq 6 -> Pazar)
        await pg.evaluate(f"(async()=>{{await save(Object.assign({{}},S.customers.get('{cid}'),{{freq:6}}));U.tab='ziyaret';U.visitFor='{cid}';render()}})()");await pg.wait_for_timeout(200)
        R["form varsayılanı Pazar değil"]=await pg.evaluate("document.querySelector('#vf_next').value")=="2026-11-16"
        await pg.evaluate("U.visitFor=null;render()")
        for tab in ["rota","daha"]:
            await pg.evaluate(f"U.tab='{tab}';render()");await pg.wait_for_timeout(150)
            R[f"yatay taşma yok ({tab})"]=await pg.evaluate("document.documentElement.scrollWidth")<=W
        await b.close()
        # Pazar günü
        b=await p.chromium.launch();ctx=await b.new_context(viewport={"width":W,"height":800});await setup(ctx);pg=await ctx.new_page();pg.on("pageerror",lambda e:errs.append(str(e)[:160]))
        await pg.clock.set_fixed_time("2026-11-15T11:00:00")  # Pazar
        await pg.goto("http://127.0.0.1:8767/boot.html");await pg.wait_for_timeout(1500)
        await pg.click("[data-act=sample]");await pg.wait_for_timeout(300);await pg.evaluate("U.tab='rota';render()")
        R["Pazar notu görünüyor"]=await pg.evaluate("!!document.querySelector('#sunNote')")
        R["Pazar iş saati değil"]=await pg.evaluate("!inWorkHours()")
        R["plan Pazar'ı atlıyor"]=await pg.evaluate("planDays(6).every(d=>!isSun(d))")
        R["Pazar taşma yok"]=await pg.evaluate("document.documentElement.scrollWidth")<=W
        await b.close()
        print(W,json.dumps(R,ensure_ascii=False))
        return [f"{W}:{k}" for k,v in R.items() if v is False],errs
async def main():
    bad=[];er=[]
    for W in (390,320):
        x,y=await run(W);bad+=x;er+=y
    print("HATALAR",bad);print("JS HATALARI:",er)
asyncio.run(main())
