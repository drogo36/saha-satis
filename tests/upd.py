import os
import asyncio,json
from playwright.async_api import async_playwright
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"qa.py")).read().split("TABS=")[0])
R_=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+"/"
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch();R={}
        # Senaryo A: GitHub'da yeni sürüm var ve dosya da yeni -> açılışta kendiliğinden güncellenir, bir kez
        ST={"ver":"2.1.0","html_ver":"2.0.1","idx":0,"loads":0}
        ctx=await b.new_context(viewport={"width":390,"height":844});await setup(ctx)
        async def raw(route):
            f=route.request.url.split("/main/")[1].split("?")[0];body=open(R_+f).read()
            if f=="version.json": body=json.dumps({"version":ST["ver"],"notes":"deneme notu"})
            if f=="index.html":
                ST["idx"]+=1;body=body.replace('const APP_VERSION="2.1.0";','const APP_VERSION="%s";'%ST["html_ver"])
            await route.fulfill(status=200,headers=H,content_type="text/plain",body=body)
        await ctx.unroute("https://raw.githubusercontent.com/**");await ctx.route("https://raw.githubusercontent.com/**",raw)
        pg=await ctx.new_page();errs=[];pg.on("pageerror",lambda e:errs.append(str(e)[:150]))
        pg.on("load",lambda: ST.__setitem__("loads",ST["loads"]+1))
        await pg.goto("http://127.0.0.1:8767/boot.html");await pg.wait_for_timeout(1200)
        R["ilk açılış sürümü"]=await pg.evaluate("APP_VERSION")
        ST["html_ver"]="2.1.0"   # GitHub artık yeni dosyayı veriyor
        await pg.wait_for_timeout(4000)
        R["kendiliğinden güncellendi"]=await pg.evaluate("APP_VERSION")
        R["güncellendi bildirimi"]=await pg.evaluate("document.querySelector('#toast').innerText")
        R["sayfa yükleme sayısı"]=ST["loads"]
        await ctx.close()
        # Senaryo B: önbellek eski dosyayı vermeye devam ediyor -> sonsuz yenileme olmamalı
        ST.update({"ver":"2.1.0","html_ver":"2.0.1","loads":0})
        ctx=await b.new_context(viewport={"width":390,"height":844});await setup(ctx);await ctx.unroute("https://raw.githubusercontent.com/**");await ctx.route("https://raw.githubusercontent.com/**",raw)
        pg=await ctx.new_page();pg.on("load",lambda: ST.__setitem__("loads",ST["loads"]+1))
        await pg.goto("http://127.0.0.1:8767/boot.html");await pg.wait_for_timeout(9000)
        R["eski dosyada yükleme sayısı (döngü yok)"]=ST["loads"]
        R["bant gösteriliyor"]=await pg.evaluate("!!document.querySelector('[data-act=doUpdate]')")
        # Senaryo C: iş yarıdayken (form açık) otomatik yenileme yapmaz
        await pg.evaluate("localStorage.removeItem('saha-guncel-deneme');U.tab='musteri';U.editCust='new';render()")
        before=ST["loads"];await pg.evaluate("checkUpdate(false,true)");await pg.wait_for_timeout(2500)
        R["form açıkken yenilemedi"]=ST["loads"]==before
        await ctx.close()
        # Senaryo D: asistana "uygulamayı güncelle" + özellik isteği
        ST.update({"ver":"2.1.0","html_ver":"2.1.0"})
        ctx=await b.new_context(viewport={"width":390,"height":844});await setup(ctx);await ctx.unroute("https://raw.githubusercontent.com/**");await ctx.route("https://raw.githubusercontent.com/**",raw)
        async def gem(route):
            out='Bunu geliştiriciye iletiyorum.\n<eylem>{"actions":[{"type":"request_feature","title":"Stok listesine raf yeri sütunu","details":"Her ürünün depodaki raf yeri görünsün."}]}</eylem>'
            await route.fulfill(status=200,headers=H,content_type="application/json",body=json.dumps({"candidates":[{"content":{"parts":[{"text":out}]}}]}))
        await ctx.unroute("https://generativelanguage.googleapis.com/**");await ctx.route("https://generativelanguage.googleapis.com/**",gem)
        await ctx.route("https://github.com/**",lambda r:r.fulfill(status=200,body="ok"))
        pg=await ctx.new_page();errs2=[];pg.on("pageerror",lambda e:errs2.append(str(e)[:150]))
        await pg.goto("http://127.0.0.1:8767/boot.html");await pg.wait_for_timeout(2000);await pg.evaluate("aiSave({key:'AIzaTEST'});U.tab='asistan';render()")
        await pg.evaluate("aiAsk('uygulamayı güncelle')");await pg.wait_for_timeout(800)
        R["asistan güncelleme cevabı"]=await pg.evaluate("U.chat[U.chat.length-1].text")
        await pg.evaluate("aiAsk('Stok listesine raf yeri sütunu eklensin')");await pg.wait_for_timeout(800)
        R["özellik isteği önizlemesi"]=await pg.evaluate("[...document.querySelectorAll('#chatList .panel .why')].map(x=>x.innerText).join(' || ')")
        async with ctx.expect_page() as np: await pg.click("[data-act=aiApply]")
        newp=await np.value;R["GitHub isteği açıldı"]=newp.url[:95]
        print(json.dumps(R,ensure_ascii=False,indent=1));print("HATALAR",errs+errs2);await b.close()
asyncio.run(main())
