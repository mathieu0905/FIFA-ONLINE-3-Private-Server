const fs = require('fs');
const vm = require('vm');
const assert = require('assert/strict');
const page = fs.readFileSync('D:/FO3ID/server/admin/index.html', 'utf8');
const script = page.match(/<script>([\s\S]*?)<\/script>/)[1];
new vm.Script(script); // Check the complete page, including unrelated existing controls.
const nodes = new Map();
const get = key => {
  if (!nodes.has(key)) nodes.set(key, {disabled: true, addEventListener(event, handler) { this[event] = handler; }});
  return nodes.get(key);
};
let inputs = [], calls = [], pending, message;
const rates = Object.fromEntries(Array.from({length:19}, (_, i) => [String(i+1), i+1]));
const data = {rates, defaults: {...rates, '6':26}, revision: 'first'};
const context = vm.createContext({
  $: get, $$: () => inputs,
  say: text => { message = text; },
  loaders: {enhancement: async () => {}},
  act: fn => { pending = fn(); },
  api: async (route, body) => { calls.push({route, body}); return {...data, rates: body.rates, revision:'saved'}; },
});
vm.runInContext(script.slice(script.indexOf('let enhancementData = null;'), script.indexOf('function renderDaily(table)')), context);
context.data = data;
vm.runInContext('renderEnhancement(data)', context);
assert.equal((get('#enhancementRows').innerHTML.match(/data-enhancement-grade=/g) || []).length, 19);
assert.match(get('#enhancementRows').innerHTML, /\+19 → \+20/);
assert.equal(get('#enhancementSave').disabled, false);
inputs = Object.entries(rates).map(([g, value]) => ({dataset:{enhancementGrade:g}, value:String(value)}));
get('#enhancementDefaults').click();
assert.equal(inputs[5].value, '26');
assert.equal(calls.length, 0); // Filling defaults never sends a save.
inputs[5].value = '12.345678901234';
get('#enhancementForm').submit({preventDefault(){}, target:{reportValidity:()=>true}});
(async () => {
  await pending;
  assert.equal(calls.length, 1);
  assert.equal(calls[0].route, 'enhancement_set');
  assert.equal(calls[0].body.revision, 'first');
  assert.equal(calls[0].body.rates['6'], 12.345678901234);
  assert.equal(Object.keys(calls[0].body.rates).length, 19);
  assert.match(get('#enhancementRows').innerHTML, /12.345678901234/);
  assert.match(message, /立即生效/);
  get('#enhancementForm').submit({preventDefault(){}, target:{reportValidity:()=>false}});
  assert.equal(calls.length, 1);
  console.log('PASS: full page JS syntax; 19 grade rows; defaults fill without save; exact decimal POST with revision; invalid form does not submit');
})().catch(error => { console.error(error); process.exitCode = 1; });
