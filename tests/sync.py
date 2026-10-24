import os
import asyncio,json,time
from playwright.async_api import async_playwright
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+"/"
H={"Access-Control-Allow-Origin":"*","Access-Control-Allow-Headers":"*"}
USERS={};DOCS={};MOCK=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"mockfb.js")).read()
def api(path,b):
    if path=="signup":
        if b["m"] in USERS: return {"error":"auth/email-already-in-use"}
        if len(b["p"])<6: return {"error":"auth/weak-password"}
        USERS[b["m"]]={"p":b["p"],"uid":"u"+str(len(USERS)+1)};return {"uid":USERS[b["m"]]["uid"],"email":b["m"]}
    if path=="login":
        u=USERS.get(b["m"])
        if not u or u["p"]!=b["p"]: return {"error":"auth/invalid-credential"}
        return {"uid":u["uid"],"email":b["m"]}
    if path=="write":
        for op in b["ops"]:
            d=dict(op["data"]); 
            if d.get("_u")=="__TS__": d["_u"]=int(time.time()*1000)
            col,_,id=op["path"].rpartition("/");DOCS.setdefault(col,{})[id]=d
        return {"ok":1}
    if path=="list": return {"docs":list(DOCS.get(b["path"],{}).values())}
    if path=="since": return {"docs":[d for d in DOCS.get(b["path"],{}).values() if d.get("_u",0)>b["t"]]}
async def device(p,origin,label,init=None):
    ctx=await (await p.chromium.launch()).new_context(viewport={"width":390,"height":844})
    async def raw(route):
        f=route.request.url.split("/main/")[1].split("?")[0];body=open(R+f).read()
        if f=="index.html": body=body.replace("const FB_CONFIG=null;","const FB_CONFIG={projectId:'test'};")
        await route.fulfill(status=200,headers=H,content_type="text/plain",body=body)
    async def gst(route):
        await route.fulfill(status=200,headers=H,content_type="application/javascript",body=MOCK if "app-compat" in route.request.url else "")
    async def mfs(route):
        if route.request.method=="OPTIONS": return await route.fulfill(status=204,headers=H)
        path=route.request.url.split("/api/")[1];res=api(path,json.loads(route.request.post_data or "{}"))
        await route.fulfill(status=200,headers=H,content_type="application/json",body=json.dumps(res))
    await ctx.route("https://raw.githubusercontent.com/**",raw);await ctx.route("https://www.gstatic.com/**",gst);await ctx.route("https://mockfs.test/**",mfs)
    for u in ["https://fonts.googleapis.com/**","https://cdnjs.cloudflare.com/**"]: await ctx.route(u,lambda r:r.abort())
    if init: await ctx.add_init_script(init)
    pg=await ctx.new_page();errs=[];pg.on("pageerror",lambda e:errs.append(label+": "+str(e)[:150]))
    await pg.goto(origin+"/boot.html");await pg.wait_for_timeout(2500);return pg,errs
async def main():
    async with async_playwright() as p:
        R_={}
        # Telefon: daha önce yerelde 3 müşterisi olan kullanıcı
        seed="if(!localStorage.getItem('seeded')){localStorage.setItem('seeded','1');localStorage.setItem('saha-satis-v1',JSON.stringify([{id:'c_tel1',kind:'customer',name:'Telefondaki Müşteri 1'},{id:'c_tel2',kind:'customer',name:'Telefondaki Müşteri 2'},{id:'setting_main',kind:'setting',target:250000}]))}"
        A,ea=await device(p,"http://127.0.0.1:8767","TELEFON",seed)
        R_["A kilitli"]=await A.evaluate("!!document.querySelector('#loginForm')&&document.querySelector('nav.bottom').hidden")
        await A.fill("#lg_mail","m@ornek.com");await A.fill("#lg_pass","123");await A.click("button[value=up]");await A.wait_for_timeout(500)
        R_["kısa şifre hatası"]=await A.evaluate("(document.querySelector('.banner')||{}).innerText||''")
        await A.fill("#lg_mail","m@ornek.com");await A.fill("#lg_pass","gizli123");await A.click("button[value=up]");await A.wait_for_timeout(1500)
        R_["A açıldı"]=await A.evaluate("!document.querySelector('#loginForm')&&!document.querySelector('nav.bottom').hidden")
        R_["buluta yüklenen"]=len(DOCS.get("users/u1/items",{}))
        # Bilgisayar: yeni cihaz, boş
        B,eb=await device(p,"http://localhost:8767","BİLGİSAYAR")
        await B.fill("#lg_mail","m@ornek.com");await B.fill("#lg_pass","yanlis99");await B.click("button[value=in]");await B.wait_for_timeout(500)
        R_["yanlış şifre"]=await B.evaluate("(document.querySelector('.banner')||{}).innerText||''")
        R_["e-posta korundu"]=await B.evaluate("document.querySelector('#lg_mail').value")
        await B.fill("#lg_pass","gizli123");await B.click("button[value=in]");await B.wait_for_timeout(1500)
        R_["B aldı"]=await B.evaluate("custList().map(c=>c.name).join(', ')+' | hedef '+settings().target")
        # B'de müşteri ekle -> A'da görünmeli
        await B.evaluate("save({id:'c_pc',kind:'customer',name:'Bilgisayardan Eklenen'})");await A.wait_for_timeout(1500)
        R_["A, B'nin eklediğini gördü"]=await A.evaluate("!!custByName('Bilgisayardan Eklenen')")
        # A'da güncelle ve sil -> B'de
        await A.evaluate("save(Object.assign({},S.customers.get('c_tel1'),{name:'Telefonda Düzenlendi'}));remove(S.customers.get('c_tel2'))");await B.wait_for_timeout(1500)
        R_["B düzenlemeyi gördü"]=await B.evaluate("!!custByName('Telefonda Düzenlendi')")
        R_["B silmeyi gördü"]=await B.evaluate("!S.customers.has('c_tel2')")
        # Yeniden açılış: tek seferlik giriş (oturum hatırlanıyor)
        await A.reload();await A.wait_for_timeout(2500)
        R_["A yeniden açınca giriş istemedi"]=await A.evaluate("!document.querySelector('#loginForm')")
        R_["A müşteri sayısı"]=await A.evaluate("S.customers.size")
        # Çıkış
        await B.evaluate("U.tab='rapor';render()");await B.click("[data-act=signOut]");await B.click("[data-act=signOut]");await B.wait_for_timeout(500)
        R_["B çıkışta kilitlendi ve temizlendi"]=await B.evaluate("!!document.querySelector('#loginForm')&&S.customers.size===0&&!localStorage.getItem('saha-satis-v1')")
        await A.evaluate("U.tab='rapor';render()");await A.wait_for_timeout(200);await A.screenshot(path=os.path.join(os.environ.get("TEST_OUT","/tmp"),"sync-rapor.png"))
        print(json.dumps(R_,ensure_ascii=False,indent=1));print("JS HATALARI:",ea+eb)
asyncio.run(main())
