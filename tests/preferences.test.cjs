const {test}=require('node:test');
const assert=require('node:assert/strict');
require('../developer_home/preferences.js');
const P=globalThis.HomePreferences;
test('corrupt or unavailable storage still opens the launcher',()=>{
 assert.equal(P.load({getItem(){return '{broken';}},{}).dim,15);
 assert.equal(P.load({getItem(){throw Error('denied');}},{}).background,'panorama');
 assert.equal(P.save({setItem(){throw Error('quota');}},{}),false);
});
test('preferences retain temporarily absent shortcuts and clamp contrast',()=>{
 const p=P.normalize({order:['b','b','temporarily-absent',17],hidden:['a','a'],dim:99},{});
 assert.deepEqual(p.order,['b','temporarily-absent']);assert.deepEqual(p.hidden,['a']);assert.equal(p.dim,70);
 assert.equal(P.normalize({dim:-5},{}).dim,0);
});
test('new apps keep configured relative order without mutating configuration',()=>{
 const items=[{id:'a'},{id:'b'},{id:'new-1'},{id:'new-2'}];
 assert.deepEqual(P.ordered(items,{order:['b','absent']}).map(x=>x.id),['b','a','new-1','new-2']);
 assert.equal(items[0].id,'a');
});
