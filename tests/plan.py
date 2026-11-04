# Gün aşırı plan: "Rotayı kontrol et" rotayı gösterir, bugünkü rotayı değiştirmez. Bağlantı yokken eski kopya değil telefondaki en güncel sürüm açılır; hafıza doluysa sessizce eski sürümde kalmaz.
import os
import asyncio,json
from playwright.async_api import async_playwright
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"qa.py")).read().split("TABS=")[0])
ANDROID="Mozilla/5.0 (Linux; Android 14; SM-A546B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36"
async def run(W):
    async with async_playwright() as p:
        b=await p.chromium.launch()
        ctx=await b.new_context(viewport={"width":W,"height":900},user_agent=ANDROID)
        await setup(ctx)
        await ctx.add_init_script("document.addEventListener('click',e=>{const a=e.target.closest('a[href]');if(a&&!/^https?:\\/\\/127/.test(a.href))e.preventDefault()},true);window.open=()=>null;")
        pg=await ctx.new_page();errs=[];pg.on("pageerror",lambda e:errs.append(str(e)[:160]))
        await pg.goto("http://127.0.0.1:8767/boot.html");await pg.wait_for_timeout(1500)
        await pg.click("[data-act=sample]");await pg.wait_for_timeout(300)
        R={}
        await pg.evaluate("save(Object.assign({},settings(),{plan:{at:today(),days:buildPlan()}}))");await pg.wait_for_timeout(300)
        await pg.evaluate("U.tab='rota';U.detail=null;render();document.querySelector('[data-act=planView]').scrollIntoView()");await pg.wait_for_timeout(200)
        R["düğme var"]=await pg.evaluate("[...document.querySelectorAll('[data-act=planView]')].every(x=>x.textContent==='Rotayı kontrol et')&&document.querySelectorAll('[data-act=planView]').length>0")
        sel0=await pg.evaluate("[...U.selected].join()")
        await pg.click("[data-act=planView] >> nth=0");await pg.wait_for_timeout(250)
        info=await pg.evaluate("""(()=>{const i=+document.querySelector('[data-act=planView]').dataset.i;const d=settings().plan.days[i];const t=document.querySelector('.planRoute').textContent;
          return {all:d.ids.every(id=>t.includes(S.customers.get(id).name)),maps:!!document.querySelector('.planRoute a[href*="google.com/maps/dir"]'),yandex:!!document.querySelector('.planRoute a[href*="yandex.com.tr"]'),svg:!!document.querySelector('.planRoute svg'),eve:t.includes('eve '),lbl:document.querySelector('[data-act=planView]').textContent,n:document.querySelectorAll('.planRoute').length}})()""")
        R["tüm duraklar görünüyor"]=info["all"];R["harita bağlantısı"]=info["maps"] and info["yandex"];R["şema var"]=info["svg"];R["eve varış"]=info["eve"];R["tek gün açık"]=info["n"]==1;R["düğme gizle oldu"]=info["lbl"]=="Rotayı gizle"
        R["bugünkü rota değişmedi"]=await pg.evaluate("[...U.selected].join()")==sel0
        R["yatay taşma yok"]=await pg.evaluate("document.documentElement.scrollWidth")<=W
        await pg.click("[data-act=planView] >> nth=0");await pg.wait_for_timeout(200)
        R["gizlendi"]=await pg.evaluate("!document.querySelector('.planRoute')")
        # silinmiş müşteri bozmasın
        R["kayıp müşteri hata vermez"]=await pg.evaluate("(()=>{const n=settings().plan.days.map(d=>d.ids).find(x=>x.length);const c=n.map(id=>S.customers.get(id)).filter(Boolean);return planRouteHTML(c.slice(0,1)).includes('planRoute')})()")
        # hafıza dolu: sessizce yenileyip eski sürümde kalmaz
        R["hafıza dolu uyarısı"]=await pg.evaluate("""(async()=>{const o=Storage.prototype.setItem;let rl=false;Storage.prototype.setItem=function(k,v){if(k==='saha-app-html')throw new DOMException('dolu','QuotaExceededError');return o.call(this,k,v)};
           await applyUpdate();Storage.prototype.setItem=o;return document.querySelector('#toast').innerText.includes('hafızası dolu')})()""")
        # bağlantı yokken: telefondaki en güncel kopya
        await pg.evaluate("navigator.serviceWorker.register('sw.js').then(()=>navigator.serviceWorker.ready)");await pg.wait_for_timeout(1500)
        R["hizmet çalışanı etkin"]=await pg.evaluate("!!navigator.serviceWorker.controller")
        await pg.evaluate("(()=>{const h=localStorage.getItem('saha-app-html');localStorage.setItem('saha-app-html',h.replace(/const APP_VERSION=\"[0-9.]+\"/,'const APP_VERSION=\"9.9.9\"'))})()")
        await ctx.set_offline(True);await pg.reload();await pg.wait_for_timeout(1800)
        R["bağlantısızda güncel sürüm"]=await pg.evaluate("APP_VERSION")
        await ctx.set_offline(False);await b.close()
        print(W,json.dumps(R,ensure_ascii=False))
        bad=[f"{W}:{k}" for k,v in R.items() if v is False]
        if R["bağlantısızda güncel sürüm"]!="9.9.9": bad.append(f"{W}:eski kopya açıldı")
        return bad,errs
async def main():
    bad=[];er=[]
    for W in (390,320):
        x,y=await run(W);bad+=x;er+=y
    print("HATALAR",bad);print("JS HATALARI:",er)
asyncio.run(main())
