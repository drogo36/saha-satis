const V="saha-1.8.0";
const CORE=["./","index.html","manifest.webmanifest","icon-192.png?v=2","icon-512.png?v=2","apple-touch-icon.png?v=2"];
const CDN="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js";
self.addEventListener("install",e=>{e.waitUntil(caches.open(V).then(async c=>{await c.addAll(CORE.map(u=>new Request(u,{cache:"reload"})));}));self.skipWaiting()});
self.addEventListener("activate",e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==V&&k!=="saha-meta").map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
self.addEventListener("fetch",e=>{const r=e.request;if(r.method!=="GET")return;const u=new URL(r.url);
  if(u.origin===location.origin){
    if(u.pathname.endsWith("version.json"))return; // always live
    const key=r.mode==="navigate"?"index.html":r;
    e.respondWith(fetch(r,{cache:"no-cache"}).then(res=>{if(res.ok){const cp=res.clone();caches.open(V).then(c=>c.put(key,cp))}return res}).catch(()=>caches.match(key).then(m=>m||caches.match("index.html"))));return}
  if(/cdnjs\.cloudflare\.com|fonts\.(googleapis|gstatic)\.com/.test(u.host)||(u.host==="www.gstatic.com"&&u.pathname.startsWith("/firebasejs/"))){
    e.respondWith(caches.match(r).then(m=>m||fetch(r).then(res=>{const cp=res.clone();caches.open(V).then(c=>c.put(r,cp));return res})))}});
self.addEventListener("notificationclick",e=>{e.notification.close();const d=e.notification.data||{};const url=d.dest||new URL(d.url||"./#ogle",self.registration.scope).href;
  e.waitUntil(self.clients.matchAll({type:"window",includeUncontrolled:true}).then(cs=>{if(!d.dest){for(const c of cs){if("focus" in c){c.navigate&&c.navigate(url);return c.focus()}}}return self.clients.openWindow(url)}))});
self.addEventListener("periodicsync",e=>{if(e.tag!=="ogle")return;const n=new Date();const m=n.getHours()*60+n.getMinutes();
  if(n.getDay()===0||m<11*60+30||m>13*60+30)return;
  e.waitUntil(caches.open("saha-meta").then(async c=>{const k=new Request("ogle-"+n.toDateString());if(await c.match(k))return;await c.put(k,new Response("1"));
    const cs=await self.clients.matchAll({type:"window"});if(cs.some(c=>c.visibilityState==="visible"))return;
    return self.registration.showNotification("🍽 TokenFlex: öğle arası",{body:"Yakınındaki TokenFlex geçen yerleri görmek için dokun.",icon:"icon-192.png",tag:"ogle",data:{url:"./#ogle"}})}))});
