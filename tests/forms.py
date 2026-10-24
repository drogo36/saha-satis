import os
import asyncio,json,sys
pass
from playwright.async_api import async_playwright
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"qa.py")).read().split("TABS=")[0])
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch();ctx=await b.new_context(timezone_id="Europe/Istanbul",viewport={"width":390,"height":800},geolocation={"latitude":41.0186,"longitude":28.9078},permissions=["geolocation"])
        await setup(ctx);pg=await ctx.new_page();await pg.clock.install(time="2026-10-24T00:40:00+03:00");issues=[];cur={"w":""}
        pg.on("pageerror",lambda e:issues.append((cur["w"],str(e)[:200])))
        await pg.goto("http://127.0.0.1:8767/boot.html");await pg.wait_for_timeout(1800)
        res={}
        # 1 empty app (no data) all tabs render
        for t in ["rota","harita","musteri","ziyaret","siparis","mesaj","asistan","rapor","daha","yakin","gunsonu"]:
            cur["w"]="boş:"+t;await pg.evaluate(f"U.tab='{t}';render()");await pg.wait_for_timeout(100)
        await pg.evaluate("U.tab='rota';render()");await pg.click("[data-act=sample]");await pg.wait_for_timeout(400)
        # 2 new customer: empty name -> blocked by required; bad geo
        cur["w"]="custForm";await pg.evaluate("U.tab='musteri';U.detail=null;U.editCust='new';render()")
        await pg.fill("#cf_name","Test Oto");await pg.fill("#cf_geo","abc");await pg.click("#custForm button[type=submit]");await pg.wait_for_timeout(300)
        res["badgeo_blocked"]=await pg.evaluate("!custByName('Test Oto')")
        await pg.fill("#cf_geo","41.01, 28.95");await pg.fill("#cf_phone","0532 111 22 33");await pg.fill("#cf_email","a@b.com");await pg.click("#custForm button[type=submit]");await pg.wait_for_timeout(400)
        res["cust_saved"]=await pg.evaluate("JSON.stringify((({name,lat,email,phone})=>({name,lat,email,phone}))(custByName('Test Oto')||{}))")
        # 3 visit form submit with result + amount text
        cur["w"]="visitForm";await pg.evaluate("U.tab='ziyaret';U.visitFor=custByName('Test Oto').id;render()")
        await pg.select_option("#vf_res","Sipariş alındı");await pg.fill("#vf_amt","12.500,50");await pg.fill("#vf_note","deneme");await pg.click("#visitForm button[type=submit]");await pg.wait_for_timeout(400)
        res["visit"]=await pg.evaluate("JSON.stringify((({result,amount})=>({result,amount}))(visitsOf(custByName('Test Oto'))[0]||{}))+' status='+custByName('Test Oto').status")
        # 4 product form + campaign
        cur["w"]="prodForm";await pg.evaluate("U.tab='stok';U.stk.edit='new';render()")
        await pg.fill("#p2_sku","BJ-01");await pg.fill("#p2_name","Buji");await pg.fill("#p2_price","95,50");await pg.fill("#p2_stock","30");await pg.click("#prodForm2 button[type=submit]");await pg.wait_for_timeout(300)
        res["prod"]=await pg.evaluate("JSON.stringify(products().find(p=>p.name==='Buji'))")
        # 5 msg cfg form
        cur["w"]="msgCfg";await pg.evaluate("U.tab='mesaj';U.msg2.tab='ayar';render()");await pg.fill("#mc_sender","Muhammed Y.");await pg.fill("#mc_depot","0532 999 88 77");await pg.click("#msgCfgForm button[type=submit]");await pg.wait_for_timeout(300)
        res["msgcfg"]=await pg.evaluate("msgCfg().sender+' / '+msgCfg().depot")
        # 6 cart with free line, discount, save
        cur["w"]="cart";await pg.evaluate("U.cart={cid:custByName('Test Oto').id,lines:[],q:'',disc:'',note:''};U.tab='satis';render()")
        await pg.fill("#freeLine input[name=name]","Özel kalem");await pg.fill("#freeLine input[name=price]","1.000");await pg.click("#freeLine button");await pg.wait_for_timeout(200)
        await pg.fill("#cartDisc","10");await pg.press("#cartDisc","Tab");await pg.wait_for_timeout(200)
        await pg.click("[data-act=cartSave]");await pg.wait_for_timeout(300)
        res["cart"]=await pg.evaluate("JSON.stringify((({amount,item,no})=>({amount,item,no}))([...S.orders.values()].find(o=>o.importedFrom==='uygulama')||{}))")
        # 7 day + lunch + target + ai forms
        cur["w"]="dayForm";await pg.evaluate("U.tab='rota';U.dayOpen=true;render()");await pg.fill("#df_by","17:30");await pg.click("#dayForm button[type=submit]");await pg.wait_for_timeout(300)
        res["day"]=await pg.evaluate("day().arriveBy")
        await pg.fill("#lf_name","Lokanta");await pg.fill("#lf_geo","41.0,28.9");await pg.click("#lunchForm button[type=submit]");await pg.wait_for_timeout(300)
        res["lunch"]=await pg.evaluate("day().lunchPlaces.length")
        cur["w"]="setForm";await pg.evaluate("U.tab='rapor';render()");await pg.fill("#sf_target","500.000");await pg.click("#setForm button[type=submit]");await pg.wait_for_timeout(300)
        res["target"]=await pg.evaluate("settings().target")
        cur["w"]="aiForm";await pg.evaluate("U.tab='asistan';render()");
        # 8 plan + route + map interactions
        cur["w"]="plan";await pg.evaluate("U.tab='rota';render()");await pg.click("[data-act=mkPlan]");await pg.wait_for_timeout(600);await pg.click("[data-act=loadPlan] >> nth=0");await pg.wait_for_timeout(300)
        res["plan_sel"]=await pg.evaluate("U.selected.size")
        cur["w"]="map";await pg.evaluate("U.tab='harita';render()");box=await pg.query_selector("#mapSvg");bb=await box.bounding_box()
        await pg.mouse.move(bb["x"]+100,bb["y"]+100);await pg.mouse.down();await pg.mouse.move(bb["x"]+180,bb["y"]+150,steps=5);await pg.mouse.up();await pg.wait_for_timeout(200)
        # 9 backup restore round trip
        cur["w"]="backup";d=await pg.evaluate("JSON.stringify({app:'saha-satis',data:[...S.customers.values(),...S.visits.values(),...S.orders.values(),...S.settings.values(),...S.products.values()]})")
        await pg.evaluate("localStorage.removeItem('saha-satis-v1')");await pg.reload();await pg.wait_for_timeout(1200)
        n0=await pg.evaluate("S.customers.size")
        await pg.evaluate("d=>restoreFrom(new File([d],'y.json'))",d);await pg.wait_for_timeout(500)
        res["restore"]=f"{n0} -> "+str(await pg.evaluate("S.customers.size+' müşteri, '+S.products.size+' ürün, hedef '+settings().target"))
        print(json.dumps(res,ensure_ascii=False,indent=1));print("JS HATALARI:",issues)
        await b.close()
asyncio.run(main())
