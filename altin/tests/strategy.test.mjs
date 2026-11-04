import assert from "node:assert";
import { percentile, rsi, readMarket, entryLevels, newAccount, step, DEFAULTS, WINDOW } from "../bot/strategy.mjs";
assert.equal(percentile([1,2,3,4,5],.5),3);
assert.equal(rsi([...Array(29).keys()].map(x=>x+1)),100);assert.equal(rsi([1,2,3]),null);
const near=(a,b,e=1e-6)=>assert.ok(Math.abs(a-b)<=e,`${a} != ${b}`);
const cfg={...DEFAULTS,spread:0,slip:0};
// elle kontrol: giriş sonraki açılışta, hedefte satış
const flat=Array.from({length:WINDOW+6},(_,i)=>({t:1.7e9+i*900,o:100,h:100,l:100,c:100}));
const a=newAccount(cfg);a.pending={resistance:102};flat[WINDOW+1].h=105;
step(a,flat,WINDOW,cfg);assert.ok(a.pos);near(a.pos.unit,100.2);
step(a,flat,WINDOW+1,cfg);const exp=1000/100.2*102*.998-1000;near(a.equity,1000+exp);assert.equal(a.trades[0].reason,"Hedef");
// zarar durdurma önce işler
const b=newAccount(cfg);b.pending={resistance:102};flat[WINDOW+2].l=90;flat[WINDOW+2].h=110;
step(b,flat,WINDOW+2,cfg);assert.equal(b.trades[0].reason,"Zarar durdurma");near(b.trades[0].sell,Math.min(100.2*.99,100));
// günlük sınır alım engeller
const seq=Array.from({length:400},(_,i)=>{const c=100000+2000*Math.sin(i/30);return{t:1.7e9+i*900,o:c,h:c+50,l:c-50,c}});
const d=newAccount(cfg);d.dayPnl=-31;d.day=new Date((seq[399].t+10800)*1000).toISOString().slice(0,10);step(d,seq,399,cfg);assert.equal(d.pending,null);
assert.equal(readMarket(seq.slice(0,50),1,2,cfg).ok,false);
console.log("altin strateji testleri geçti");
