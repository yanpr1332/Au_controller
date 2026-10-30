const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../cep/com.openai.audition.inspector/client/diagnostics.js'), 'utf8');
for (const initialWidth of [0, 540]) {
  const events = {}, calls = [], resizes = [];
  const body = {clientWidth: initialWidth, clientHeight: 169, style: {}};
  const document = {body, readyState:'complete', addEventListener:(name,fn)=>events[name]=fn};
  const window = {
    innerWidth:initialWidth, innerHeight:initialWidth ? 440 : 0, devicePixelRatio:1.5,
    getComputedStyle:()=>({backgroundColor:'rgb(32, 35, 42)',visibility:'visible'}),
    addEventListener:(name,fn)=>events[name]=fn,
    requestAnimationFrame:fn=>fn(), setTimeout:fn=>fn(),
    __adobe_cep__:{
      resizeContent:(w,h)=>{resizes.push([w,h]);window.innerWidth=w;window.innerHeight=h;},
      evalScript:(script,callback)=>{new vm.Script(script);calls.push(script);callback('RECORDED');}
    }
  };
  vm.runInNewContext(source,{window,document,console:{log(){},error(){}}});
  events.DOMContentLoaded();events.load();events.error({message:'Quote " and newline\n'});
  assert.equal(resizes.length,initialWidth ? 0 : 1);
  assert.ok(calls.length>=4);
  assert.ok(calls.every(x=>x.includes('tests/receipts/cep_page_')));
  assert.equal(body.style.transform,'none');
}
console.log('CEP diagnostic tests passed: zero-size repair, valid-size guard, generated JSX escaping, bounded repaint');
