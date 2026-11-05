# Rotada olmayan müşterinin yanında kalınca uygulama yalnızca sorar; kendiliğinden başlatmaz. Sanayi sitesinde art arda rahatsız etmez.
import os
import asyncio,json
from playwright.async_api import async_playwright
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"qa.py")).read().split("TABS=")[0])
FAR={"latitude":39.5,"longitude":32.5}
X={"latitude":41.05,"longitude":28.80}
SEED="""(()=>{const a=(id,name,lat,lng,x)=>put(Object.assign({id,kind:'customer',name,status:'Aktif',tier:'B',lat,lng},x||{}));
 a('x','Yakın Oto X',41.05,28.80);a('y','Komşu Oto Y',41.0503,28.80);a('p','Pasif Oto',41.20,28.80,{status:'Pasif'});a('v','Bugün Gidilen',41.30,28.80);a('r','Rotadaki Oto',41.40,28.80);a('h','Ev Yanı Oto',41.0115,29.2135);
 put({id:'v1',kind:'visit',customerId:'v',customerName:'Bugün Gidilen',date:today(),start:'09:00',end:'09:30',result:'Görüşüldü'});DV++;U.tab='musteri';U.detail=null;U.nearDwell=200;U.arrDwell=200;U.arrFixMs=100;render();return 1})()"""
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        ctx=await b.new_context(timezone_id="Europe/Istanbul",viewport={"width":320,"height":800},geolocation=FAR,permissions=["geolocation"])
        await setup(ctx)
        pg=await ctx.new_page();errs=[];pg.on("pageerror",lambda e:errs.append(str(e)[:160]))
        await pg.clock.set_fixed_time("2026-11-04T07:30:00Z")  # 10:30 İstanbul, mesai içinde
        await pg.goto("http://127.0.0.1:8767/boot.html");await pg.wait_for_timeout(1500)
        ev=pg.evaluate;wait=pg.wait_for_timeout;R={}
        await ev(SEED);await wait(200)
        geo=lambda g:ctx.set_geolocation(g)
        near=lambda:ev("U.nearAsk")
        reset="nearClear();U.nearQuiet=0;U.arrSkip=null;U.live=null;render()"
        R["uzaktayken sormuyor"]=await near() is None or await ev("!U.nearAsk")
        # 110 m: fazla uzak
        await geo({"latitude":41.049,"longitude":28.80});await wait(600)
        R["110 m'de sormuyor"]=await ev("!U.nearAsk&&!U.nearCand")
        await geo(FAR);await wait(150)
        # bekleme bitmeden uzaklaşma
        await ev("U.nearDwell=3000");await geo(X);await wait(200)
        R["aday oldu ama sormadı"]=await ev("!!U.nearCand&&!U.nearAsk")
        await geo(FAR);await wait(200)
        R["uzaklaşınca aday düştü"]=await ev("!U.nearCand&&!U.nearAsk")
        await ev("U.nearDwell=200")
        # araçla geçiş
        await ev("arrivalCheck({lat:41.05,lng:28.80,acc:10,speed:14})");R["araçla geçerken sormuyor"]=await ev("!U.nearCand")
        await ev("arrivalCheck({lat:41.05,lng:28.80,acc:80,speed:0})");R["konum net değilse sormuyor"]=await ev("!U.nearCand")
        # soru
        await geo(X);await wait(700)
        R["kalınca soruyor"]=await near()=="x" and await ev("!!document.querySelector('#nearBanner')")
        R["kendiliğinden başlatmıyor"]=await ev("!U.live")
        R["başka sekmede de görünüyor"]=await ev("U.tab==='musteri'&&document.querySelector('#nearBanner').innerText.includes('Yakın Oto X')")
        R["taşma yok"]=await ev("document.documentElement.scrollWidth")<=320
        # Başlat
        await pg.click("#nearBanner [data-act=nearStart]");await wait(200)
        R["başlat çalışıyor"]=await ev("U.live&&U.live.customerId")=="x" and await ev("U.live.start")=="10:30" and await ev("!document.querySelector('#nearBanner')")
        await ev("U.tab='rota';render()");await wait(100)
        R["ziyarette paneli"]="Ziyarette" in await ev("document.querySelector('.panel.live').innerText")
        await ev("U.tab='musteri';"+reset);await geo(FAR);await wait(200)
        # Hayır: bu müşteri bugünlük, komşular 30 dakika
        await geo(X);await wait(700)
        await pg.click("#nearBanner [data-act=nearNo]");await wait(150)
        R["Hayır soruyu kapatıyor"]=await ev("!U.nearAsk&&!document.querySelector('#nearBanner')")
        Y={"latitude":41.0503,"longitude":28.80}
        await geo(Y);await wait(700)
        R["komşu müşteri 30 dk sorulmuyor"]=await ev("!U.nearAsk&&!U.nearCand")
        await ev("U.nearQuiet=0");await geo({"latitude":41.05031,"longitude":28.80});await wait(700)
        R["süre dolunca komşu soruluyor"]=await near()=="y"
        await ev("nearClear();U.nearQuiet=0");await geo(X);await wait(600)
        R["Hayır dediğin bugün sorulmuyor"]=await near()!="x"
        await ev(reset);await geo(FAR);await wait(150)
        # kapsam dışı: pasif, bugün ziyaret edilen, evin yanı
        for k,g in (("pasif",{"latitude":41.20,"longitude":28.80}),("bugün gidilen",{"latitude":41.30,"longitude":28.80}),("ev yanı",{"latitude":41.0115,"longitude":29.2135})):
            await geo(g);await wait(500);R[k+" sorulmuyor"]=await ev("!U.nearAsk&&!U.nearCand");await geo(FAR);await wait(120)
        # rotadaki müşteri kendi akışıyla başlar, soru çıkmaz
        await ev("U.selected=new Set(['r']);keepUI();render()");await wait(100);await geo({"latitude":41.40,"longitude":28.80});await wait(800)
        R["rotadaki müşteri otomatik başlıyor"]=await ev("U.live&&U.live.customerId")=="r" and await ev("!U.nearAsk")
        await ev("U.selected=new Set();keepUI();"+reset);await geo(FAR);await wait(200)
        # açık ziyaret varken sormaz
        await ev("U.live={customerId:'r',start:'09:00',date:today()};render()");await geo(X);await wait(600)
        R["açık ziyarette sormuyor"]=await ev("!U.nearAsk&&!U.nearCand")
        await ev(reset);await geo(FAR);await wait(150)
        # ayar kapalı
        await ev("U.tab='rota';U.dayOpen=true;render()");await wait(100);await pg.click("[data-act=nearAsk]");await wait(250)
        R["ayar kapandı"]=await ev("day().nearAsk===false") and "Kapalı" in await ev("document.querySelector('[data-act=nearAsk]').innerText")
        await geo(X);await wait(600);R["kapalıyken sormuyor"]=await ev("!U.nearAsk&&!U.nearCand")
        await ev("saveDay({nearAsk:true})");await wait(150);await geo(FAR);await wait(150)
        # mesai dışı
        await pg.clock.set_fixed_time("2026-11-04T18:30:00Z");await ev("render()");await geo(X);await wait(600)
        R["mesai dışında sormuyor"]=await ev("!U.nearAsk&&!U.nearCand")
        await b.close()
        print(json.dumps(R,ensure_ascii=False))
        print("HATALAR",[k for k,v in R.items() if v is False]);print("JS HATALARI:",errs)
asyncio.run(main())
