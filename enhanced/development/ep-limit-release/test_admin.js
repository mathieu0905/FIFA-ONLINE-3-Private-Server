const fs=require('fs'),vm=require('vm'),assert=require('assert');
const page=fs.readFileSync(__dirname+'/server/admin/index.html','utf8');
const fields={'#epValue':{value:''},'#epForm':{addEventListener:(name,fn)=>{if(name==='click')context.onClick=fn;}}};
let sent;
const context={BigInt,Number,console,t:(key,...args)=>key==='locale'?'zh-CN':key,
  $:key=>fields[key],say:()=>{},act:fn=>fn(),api:async(name,body)=>{sent=JSON.parse(JSON.stringify(body));return {ep_exact:'100000000000000001'};},
  loaders:{ringkasan:async()=>{}},onClick:null};
vm.createContext(context);
const helpers=page.slice(page.indexOf('const fmtEpExact ='),page.indexOf('const esc ='));
const handlers=page.slice(page.indexOf('$("#epForm").addEventListener'),page.indexOf('$("#playerFilter").addEventListener'));
vm.runInContext(helpers+'\n'+handlers,context);
(async()=>{
  assert.strictEqual(vm.runInContext('fmtEp("1000000000000")',context),'1兆');
  assert.strictEqual(vm.runInContext('fmtEp("10000000000000000")',context),'1京');
  assert.strictEqual(vm.runInContext('fmtEpExact("100000000000000001")',context),'100,000,000,000,000,001');
  for(const [mode,key,value] of [['set','set','100000000000000001'],['add','add','100000000000000001'],['sub','add','-100000000000000001']]){
    fields['#epValue'].value='100000000000000001';sent=null;
    await context.onClick({target:{dataset:{mode}},preventDefault(){}});
    assert.strictEqual(sent[key],value);
  }
  for(const value of ['1.5','1e18','-1','1000000000000000001','']){
    fields['#epValue'].value=value;sent=null;
    await context.onClick({target:{dataset:{mode:'set'}},preventDefault(){}});assert.strictEqual(sent,null);
  }
  const report={status:'PASS',exact_decimal_strings:true,bigint_display:true,invalid_input_rejected:true};
  fs.writeFileSync(__dirname+'/admin-test-result.json',JSON.stringify(report,null,2));console.log(report);
})();
