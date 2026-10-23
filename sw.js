const V="saha-1.1.0";
const CORE=["./","index.html","manifest.webmanifest","icon-192.png","icon-512.png","apple-touch-icon.png"];
const CDN="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js";
self.addEventListener("install",e=>{e.waitUntil(caches.open(V).then(async c=>{await c.addAll(CORE.map(u=>new Request(u,{cache:"reload"})));try{await c.add(new Request(CDN,{mode:"no-cors"}))}catch(_){}}));self.skipWaiting()});
self.addEventListener("activate",e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==V).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
self.addEventListener("fetch",e=>{const r=e.request;if(r.method!=="GET")return;const u=new URL(r.url);
  if(u.origin===location.origin){
    if(u.pathname.endsWith("version.json"))return; // always live
    const key=r.mode==="navigate"?"index.html":r;
    e.respondWith(fetch(r,{cache:"no-cache"}).then(res=>{if(res.ok){const cp=res.clone();caches.open(V).then(c=>c.put(key,cp))}return res}).catch(()=>caches.match(key).then(m=>m||caches.match("index.html"))));return}
  if(/cdnjs\.cloudflare\.com|fonts\.(googleapis|gstatic)\.com/.test(u.host)){
    e.respondWith(caches.match(r).then(m=>m||fetch(r).then(res=>{const cp=res.clone();caches.open(V).then(c=>c.put(r,cp));return res})))}});
