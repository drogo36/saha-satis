(function(){const API="https://mockfs.test/api/";
 async function call(p,b){const r=await fetch(API+p,{method:"POST",body:JSON.stringify(b||{})});const j=await r.json();if(j.error){const e=new Error(j.error);e.code=j.error;throw e}return j}
 const wrap=d=>{if(d&&typeof d._u==="number"){const n=d._u;d._u={toMillis:()=>n}}return d};
 let user=null;try{user=JSON.parse(localStorage.getItem("mockauth")||"null")}catch(e){}
 const subs=[];const fire=()=>subs.forEach(f=>setTimeout(()=>f(user),10));
 const auth={get currentUser(){return user},onAuthStateChanged(f){subs.push(f);setTimeout(()=>f(user),30)},
  async signInWithEmailAndPassword(m,p){user=await call("login",{m,p});localStorage.setItem("mockauth",JSON.stringify(user));fire()},
  async createUserWithEmailAndPassword(m,p){user=await call("signup",{m,p});localStorage.setItem("mockauth",JSON.stringify(user));fire()},
  async signOut(){user=null;localStorage.removeItem("mockauth");fire()},async sendPasswordResetEmail(){}};
 function Coll(path){return {path,doc:id=>({id,path:path+"/"+id,collection:n=>Coll(path+"/"+id+"/"+n)}),
  async get(){const j=await call("list",{path});return {forEach:f=>j.docs.forEach(d=>f({id:d.id,data:()=>wrap(d)}))}},
  where(f,op,ts){const q={onSnapshot(cb,err){let t=ts.toMillis();const iv=setInterval(async()=>{try{const j=await call("since",{path,t});if(j.docs.length){t=Math.max(t,...j.docs.map(d=>d._u));
     cb({docChanges:()=>j.docs.map(d=>({type:"added",doc:{id:d.id,metadata:{hasPendingWrites:false},data:()=>wrap(Object.assign({},d))}}))})}}catch(e){}},250);return ()=>clearInterval(iv)}};return q}}}
 const db={async enablePersistence(){},collection:n=>Coll(n),batch(){const ops=[];return {set(ref,data){ops.push({path:ref.path,data})},async commit(){await call("write",{ops})}}}};
 window.firebase={initializeApp(){},auth:()=>auth,firestore:Object.assign(()=>db,{Timestamp:{fromMillis:ms=>({toMillis:()=>ms})},FieldValue:{serverTimestamp:()=>"__TS__"}})};
})();
