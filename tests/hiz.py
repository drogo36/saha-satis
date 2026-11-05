# Çok duraklı rota telefonu dondurmamalı; açık ziyarette ayrılış hatırlatılır; konumu olmayan müşterinin konumu ziyaretten kaydedilir.
import os
import asyncio,json
from playwright.async_api import async_playwright
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"qa.py")).read().split("TABS=")[0])
SEED="""(()=>{for(let i=0;i<800;i++)put({id:'c'+i,kind:'customer',name:'Firma '+i,status:'Aktif',tier:'ABC'[i%3],lat:40.9+((i*37)%200)/1000,lng:28.8+((i*91)%500)/1000});
 put({id:'ng',kind:'customer',name:'Konumsuz Oto',status:'Aktif',tier:'B'});DV++;return 1})()"""
async def run():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        ctx=await b.new_context(timezone_id="Europe/Istanbul",viewport={"width":390,"height":800},geolocation={"latitude":39.5,"longitude":32.5},permissions=["geolocation"])
        await setup(ctx)
        pg=await ctx.new_page();errs=[];pg.on("pageerror",lambda e:errs.append(str(e)[:160]))
        await pg.goto("http://127.0.0.1:8767/boot.html");await pg.wait_for_timeout(1500)
        ev=pg.evaluate;wait=pg.wait_for_timeout
        await ev(SEED);R={}
        T="""(n,force)=>{U.tab='rota';U.detail=null;U.forceAll=force;U.selected=new Set([...Array(n).keys()].map(i=>'c'+i));_brC=null;const a=performance.now();const r=buildRoute();const m=performance.now()-a;const a2=performance.now();buildRoute();return {ms:Math.round(m),again:Math.round(performance.now()-a2),order:r.order.length,over:r.overflow.length,ok:r.plan.ok}}"""
        r=await ev(T,[800,False]) if False else await pg.evaluate("(a)=>("+T+")(a[0],a[1])",[800,False])
        print("800 durak",r)
        R["800 durak donmuyor"]=r["ms"]<1500
        R["800 durak: hepsi hesapta"]=r["order"]+r["over"]==800
        R["800 durak: güne sığan sayıda"]=r["order"]<=25
        R["tekrar hesap önbellekten"]=r["again"]<20
        r=await pg.evaluate("(a)=>("+T+")(a[0],a[1])",[800,True]);print("800 durak hepsi",r)
        R["800 durak, hepsi zorla donmuyor"]=r["ms"]<3000 and r["order"]==800
        r=await pg.evaluate("(a)=>("+T+")(a[0],a[1])",[120,False]);print("120 durak",r)
        R["120 durak hızlı"]=r["ms"]<500
        r=await pg.evaluate("(a)=>("+T+")(a[0],a[1])",[12,False]);print("12 durak",r)
        R["az durakta hepsi hesapta"]=r["order"]+r["over"]==12
        await ev("U.forceAll=false;render()");await wait(100)
        R["ekran çiziliyor"]=await ev("!!document.querySelector('#app .panel')")
        # ayrılış: müşterinin yanından uzaklaşınca hatırlatır, bitiş saati hazır gelir, ziyareti kapatmaz
        c=await ev("(()=>{const c=S.customers.get('c0');return {lat:c.lat,lng:c.lng}})()")
        await ev("U.arrDwell=100;U.arrFixMs=100;U.selected=new Set(['c0']);keepUI();render()");await wait(100)
        await ctx.set_geolocation({"latitude":c["lat"],"longitude":c["lng"]});await wait(1000)
        R["varışta başladı"]=await ev("U.live&&U.live.customerId")=="c0"
        await ctx.set_geolocation({"latitude":c["lat"]+0.001,"longitude":c["lng"]});await wait(300)
        R["yakınken ayrıldı sayılmıyor"]=await ev("!U.live.left")
        await ctx.set_geolocation({"latitude":c["lat"]+0.01,"longitude":c["lng"]});await wait(400)
        R["ayrılış algılandı"]=await ev("!!U.live.left")
        R["ziyaret açık kaldı"]=await ev("U.live.customerId")=="c0"
        R["panelde yazıyor"]="ayrıldın" in await ev("document.querySelector('.panel.live').innerText")
        left=await ev("U.live.left")
        await ctx.set_geolocation({"latitude":c["lat"],"longitude":c["lng"]});await wait(300)
        R["geri dönünce hatırlatma kalkıyor"]=await ev("!U.live.left")
        await ctx.set_geolocation({"latitude":c["lat"]+0.01,"longitude":c["lng"]});await wait(300)
        left=await ev("U.live.left")
        await pg.click(".panel.live [data-act=visit]");await wait(200)
        R["bitiş saati ayrılış saati"]=await ev("document.querySelector('#vf_end').value")==left
        await ev("U.visitFor=null;U.tab='rota';U.detail=null;U.live=null;keepUI();render()")
        # uzaktan elle başlatılan ziyaret "ayrıldın" demez
        await ev("U.live={customerId:'c0',start:'09:00',date:today()};render()");await ctx.set_geolocation({"latitude":c["lat"]+0.02,"longitude":c["lng"]});await wait(300)
        R["hiç gitmediysen ayrıldın demiyor"]=await ev("!U.live.left")
        # konumsuz müşteri: ziyaretten konum kaydı ve geri al
        await ev("U.live={customerId:'ng',start:'10:00',date:today()};U.selected=new Set(['ng']);keepUI();render()");await wait(150)
        await ctx.set_geolocation({"latitude":41.01,"longitude":29.01});await wait(300)
        await pg.click(".panel.live [data-act=liveGeo]");await wait(500)
        R["konum kaydedildi"]=await ev("(()=>{const c=S.customers.get('ng');return c.lat===41.01&&c.lng===29.01&&c.name==='Konumsuz Oto'})()")
        R["düğme kalktı"]=await ev("!document.querySelector('[data-act=liveGeo]')")
        await pg.click("#toast button");await wait(200)
        R["geri alındı"]=await ev("!hasGeo(S.customers.get('ng'))&&S.customers.get('ng').name==='Konumsuz Oto'")
        R["yatay taşma yok"]=await ev("document.documentElement.scrollWidth")<=390
        await b.close()
        print(json.dumps(R,ensure_ascii=False))
        return [k for k,v in R.items() if v is False],errs
async def main():
    x,y=await run();print("HATALAR",x);print("JS HATALARI:",y)
asyncio.run(main())
