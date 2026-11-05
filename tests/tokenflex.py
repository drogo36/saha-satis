# Öğle arası: "TokenFlex'te ara" kutusunda konuma en yakın yer hazır gelir; düğme adı kopyalar, siteyi yeni sekmede açar; yazılan ad korunur.
import os
import asyncio,json
from playwright.async_api import async_playwright
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"qa.py")).read().split("TABS=")[0])
FOOD={"elements":[{"type":"node","lat":41.0170,"lon":28.9050,"tags":{"amenity":"cafe","name":"Mavi Kafe"}},
 {"type":"node","lat":41.0190,"lon":28.9080,"tags":{"amenity":"restaurant","name":"Hacı \"Usta\" Lokantası"}},
 {"type":"way","center":{"lat":41.0200,"lon":28.9100},"tags":{"amenity":"fast_food","name":"Köşe Büfe"}}]}
NEAR='Hacı "Usta" Lokantası'
async def run(W):
    async with async_playwright() as p:
        b=await p.chromium.launch()
        ctx=await b.new_context(viewport={"width":W,"height":900},geolocation={"latitude":41.0186,"longitude":28.9078},permissions=["geolocation"])
        await setup(ctx)
        async def ov(r):
            await r.fulfill(status=200,headers=H,content_type="application/json",body=json.dumps(FOOD))
        await ctx.unroute("https://overpass-api.de/**");await ctx.route("https://overpass-api.de/**",ov)
        # kopyalanan metin kaydedilsin; site gerçekten yeni sekmede açılsın ama sahte sayfa dönsün
        await ctx.route("https://www.tokenflex.com.tr/**",lambda r:r.fulfill(status=200,content_type="text/html",body="<p>tf</p>"))
        pages=[];ctx.on("page",lambda x:pages.append(x))
        await ctx.add_init_script("window.__clip=[];Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:t=>{window.__clip.push(t);return Promise.resolve()}}});")
        pg=await ctx.new_page();errs=[];pg.on("pageerror",lambda e:errs.append(str(e)[:160]))
        await pg.clock.set_fixed_time("2026-11-04T09:30:00")
        await pg.goto("http://127.0.0.1:8767/boot.html");await pg.wait_for_timeout(1500)
        await pg.click("[data-act=sample]");await pg.wait_for_timeout(300)
        await pg.evaluate("saveDay({lunchPlaces:[]})");await pg.evaluate("U.tab='rota';U.lunch.open=true;render()");await pg.wait_for_timeout(200)
        R={}
        R["konum yokken kutu çıkmıyor"]=await pg.evaluate("!document.querySelector('#tf_q')")
        await pg.click("[data-act=lunchLocate]");await pg.wait_for_timeout(900)
        val=lambda:pg.evaluate("document.querySelector('#tf_q').value")
        R["kutuda en yakın yer var"]=(await val())==NEAR
        n0=len(pages);await pg.click("#tfSearch [data-act=tfSearch]");await pg.wait_for_timeout(500)
        R["ad kopyalandı"]=(await pg.evaluate("window.__clip[window.__clip.length-1]"))==NEAR
        R["site yeni sekmede açılıyor"]=len(pages)==n0+1 and pages[-1].url=="https://www.tokenflex.com.tr/uye-is-yeri"
        R["bilgi mesajı"]=await pg.evaluate("document.querySelector('#toast').innerText.includes('kopyalandı')")
        # satırdaki düğme kendi yerini kopyalar
        await pg.evaluate("[...document.querySelectorAll('#ogle .list .item')].find(i=>i.innerText.includes('Mavi Kafe')).querySelector('[data-act=tfSearch]').click()");await pg.wait_for_timeout(200)
        R["satır düğmesi kendi adını kopyalıyor"]=(await pg.evaluate("window.__clip[window.__clip.length-1]"))=="Mavi Kafe"
        # işaretlenince sıradaki en yakına geçer
        await pg.evaluate("[...document.querySelectorAll('#ogle [data-act=lunchNo]')][0].click()");await pg.wait_for_timeout(400)
        R["işaretleyince sıradakine geçiyor"]=(await val())!=NEAR and bool(await val())
        # elle yazılan ad yenilemede kaybolmaz ve kopyalanır
        await pg.fill("#tf_q","Benim Lokantam");await pg.evaluate("render()");await pg.wait_for_timeout(150)
        R["yazılan ad korunuyor"]=(await val())=="Benim Lokantam"
        await pg.click("#tfSearch [data-act=tfSearch]");await pg.wait_for_timeout(200)
        R["yazılan ad kopyalandı"]=(await pg.evaluate("window.__clip[window.__clip.length-1]"))=="Benim Lokantam"
        # kopyalama başarısızsa ad gösterilir, uygulama bozulmaz
        await pg.evaluate("void(navigator.clipboard.writeText=()=>Promise.reject(new Error('izin yok')))")
        await pg.click("#tfSearch [data-act=tfSearch]");await pg.wait_for_timeout(200)
        R["kopyalanamayınca adı söylüyor"]=await pg.evaluate("document.querySelector('#toast').innerText.includes('Benim Lokantam')")
        R["yatay taşma yok"]=await pg.evaluate("document.documentElement.scrollWidth")<=W
        await b.close()
        print(W,json.dumps(R,ensure_ascii=False))
        return [f"{W}:{k}" for k,v in R.items() if v is False],errs
async def main():
    bad=[];er=[]
    for W in (390,320):
        x,y=await run(W);bad+=x;er+=y
    print("HATALAR",bad);print("JS HATALARI:",er)
asyncio.run(main())
