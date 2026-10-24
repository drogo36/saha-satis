import os
import asyncio,json,sys
from playwright.async_api import async_playwright
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+"/"
W=int(sys.argv[1]) if len(sys.argv)>1 else 390
H={"Access-Control-Allow-Origin":"*"}
async def setup(ctx):
    async def raw(route):
        f=route.request.url.split("/main/")[1].split("?")[0]
        await route.fulfill(status=200,headers=H,content_type="text/plain",body=open(R+f).read())
    await ctx.route("https://raw.githubusercontent.com/**",raw)
    await ctx.route("https://fonts.googleapis.com/**",lambda r:r.abort())
    await ctx.route("https://cdnjs.cloudflare.com/**",lambda r:r.abort())
    await ctx.route("https://overpass-api.de/**",lambda r:r.fulfill(status=200,headers=H,content_type="application/json",body=json.dumps({"elements":[{"type":"node","lat":41.019,"lon":28.909,"tags":{"shop":"car_parts","name":"Yıldırım Oto Parça"}}]})))
    await ctx.route("https://nominatim.openstreetmap.org/**",lambda r:r.fulfill(status=200,headers=H,content_type="application/json",body=json.dumps({"name":"X","address":{"road":"Y Sk","town":"Zeytinburnu","province":"İstanbul"}} if "reverse" in r.request.url else [{"lat":"41.0","lon":"28.9"}])))
    await ctx.route("https://photon.komoot.io/**",lambda r:r.fulfill(status=200,headers=H,content_type="application/json",body=json.dumps({"features":[]})))
    await ctx.route("https://generativelanguage.googleapis.com/**",lambda r:r.fulfill(status=200,headers=H,content_type="application/json",body=json.dumps({"candidates":[{"content":{"parts":[{"text":"{\"result\":\"Teklif verildi\",\"amount\":100,\"parts\":\"x\",\"note\":\"y\",\"nextVisit\":\"\"}"}]}}]})))
    await ctx.route("https://*.pollinations.ai/**",lambda r:r.abort())
    await ctx.route("https://wa.me/**",lambda r:r.abort())
    await ctx.route("https://www.google.com/**",lambda r:r.abort())
    await ctx.route("https://aistudio.google.com/**",lambda r:r.abort())
TABS=["stok","rota","harita","musteri","ziyaret","siparis","mesaj:odeme","mesaj:kampanya","mesaj:stok","mesaj:ayar","mesaj:gecmis","asistan","rapor","daha","yakin","gunsonu","satis","detail","visitform","custform"]
async def goto(pg,t):
    js={"detail":"U.tab='musteri';U.detail=custList()[0].id;render()",
        "visitform":"U.tab='ziyaret';U.detail=null;U.visitFor=custList()[0].id;render()",
        "custform":"U.tab='musteri';U.detail=null;U.editCust=custList()[0].id;render()",
        "satis":"U.cart={cid:custList()[0].id,lines:[],q:'',disc:'',note:''};U.tab='satis';U.detail=null;render()"}.get(t)
    if not js:
        if t.startswith("mesaj:"): js=f"U.tab='mesaj';U.detail=null;U.msg2.tab='{t[6:]}';render()"
        else: js=f"U.tab='{t}';U.detail=null;U.visitFor=null;U.editCust=null;render()"
    await pg.evaluate(js);await pg.wait_for_timeout(150)
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        ctx=await b.new_context(timezone_id="Europe/Istanbul",viewport={"width":W,"height":800},geolocation={"latitude":41.0186,"longitude":28.9078},permissions=["geolocation","clipboard-read","clipboard-write"],user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1")
        await setup(ctx)
        await ctx.add_init_script("document.addEventListener('click',e=>{const a=e.target.closest('a[href]');if(a&&!/^https?:\\/\\/127/.test(a.href))e.preventDefault()},true);window.open=()=>null;")
        pg=await ctx.new_page();issues=[]
        cur={"where":""}
        pg.on("pageerror",lambda e:issues.append(("JS",cur["where"],str(e)[:160])))
        pg.on("console",lambda m:issues.append(("CONSOLE",cur["where"],m.text[:160])) if m.type=="error" and "ERR_" not in m.text and "Failed to load" not in m.text else None)
        await pg.goto("http://127.0.0.1:8767/boot.html");await pg.wait_for_timeout(1800)
        await pg.click("[data-act=sample]");await pg.wait_for_timeout(500)
        await pg.evaluate("aiSave({key:'AIzaTEST'})")
        snap=await pg.evaluate("JSON.stringify(Object.assign({},localStorage))")
        clicks=0
        for t in TABS:
            cur["where"]=t
            await goto(pg,t)
            ov=await pg.evaluate(f"""(()=>{{const out=[];const vw={W};document.querySelectorAll('#app *').forEach(el=>{{const r=el.getBoundingClientRect();if(r.width&&r.right>vw+1){{let p=el.parentElement,ok=false;while(p){{const cs=getComputedStyle(p);if(/(auto|scroll|hidden)/.test(cs.overflowX)&&p.scrollWidth>p.clientWidth){{ok=true;break}}p=p.parentElement}}if(!ok)out.push(el.tagName+'.'+(el.className||'')+':'+(el.textContent||'').trim().slice(0,30))}}}});return {{sw:document.documentElement.scrollWidth,ov:out.slice(0,5)}}}})()""")
            if ov["sw"]>W or ov["ov"]: issues.append(("OVERFLOW",t,json.dumps(ov,ensure_ascii=False)[:300]))
            n=await pg.evaluate("document.querySelectorAll('#app [data-act]:not(input):not(select), #app [data-goto-tab]').length")
            for i in range(n):
                await pg.evaluate("s=>{localStorage.clear();Object.entries(JSON.parse(s)).forEach(([k,v])=>localStorage.setItem(k,v))}",snap)
                await pg.reload();await pg.wait_for_timeout(500)
                await goto(pg,t)
                info=await pg.evaluate(f"(()=>{{const el=[...document.querySelectorAll('#app [data-act]:not(input):not(select), #app [data-goto-tab]')][{i}];if(!el)return null;return (el.dataset.act||'goto:'+el.dataset.gotoTab)+' | '+(el.textContent||el.alt||'').trim().slice(0,30)}})()")
                if not info: continue
                cur["where"]=t+" → "+info
                if any(k in info for k in ["doUpdate"]): continue
                try:
                    await pg.evaluate(f"[...document.querySelectorAll('#app [data-act]:not(input):not(select), #app [data-goto-tab]')][{i}].click()")
                    await pg.wait_for_timeout(350);clicks+=1
                    # second click for two-step confirms
                    if "delete" in info.lower() or info.startswith("del"):
                        await pg.evaluate(f"(()=>{{const el=[...document.querySelectorAll('#app [data-sure]')][0];if(el)el.click()}})()");await pg.wait_for_timeout(300)
                except Exception as e: issues.append(("CLICK",cur["where"],str(e)[:120]))
                alive=await pg.evaluate("!!document.querySelector('#app')&&document.querySelector('#app').innerHTML.length>50")
                if not alive: issues.append(("BLANK",cur["where"],"ekran boş kaldı"))
        # sheet buttons
        for act in ["quick","openSearch"]:
            cur["where"]="sheet:"+act
            await pg.evaluate(f"U.tab='rota';render();document.querySelector('[data-act={act}]').click()");await pg.wait_for_timeout(300)
            k=await pg.evaluate("document.querySelectorAll('#sheet [data-act],#sheet [data-goto-tab]').length")
            if k==0: issues.append(("SHEET",act,"boş"))
            await pg.evaluate("document.querySelector('#sheet [data-act=closeSheet]')?.click()")
        print("TIKLAMA",clicks,"SORUN",len(issues))
        seen=set()
        for x in issues:
            key=(x[0],x[2])
            if key in seen: continue
            seen.add(key);print(" - ",x[0],"|",x[1],"|",x[2])
        await b.close()
asyncio.run(main())
