// Browser-independent regression test for cancellation/reset races.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
class Element {
  constructor() { this.children=[]; this.dataset={}; this.style={}; this.listeners={}; this.value=''; this.disabled=false; this.isConnected=true; }
  append(child) { this.children.push(child); child.parent=this; }
  replaceChildren(...children) { for(const c of this.children)c.isConnected=false; this.children=children; }
  remove() { this.isConnected=false; if(this.parent)this.parent.children=this.parent.children.filter(c=>c!==this); }
  setAttribute() {}
  addEventListener(name,fn) { this.listeners[name]=fn; }
  focus() { this.focused=true; }
  scrollIntoView() { this.scrolled=true; }
  get firstChild() { return this.children[0]; }
  cloneNode() { const copy=new Element(); copy.phrase={dataset:{i18n:'welcome'}}; return copy; }
  querySelector() { return this.phrase; }
}
async function main() {
  const ids=Object.fromEntries(['messages','question','chat-form','send','welcome','clear','language'].map(id=>[id,new Element()]));
  const queue=[];
  const context=vm.createContext({
    URL,AbortController,setTimeout,clearTimeout,console,
    document:{documentElement:{},getElementById:id=>ids[id],querySelectorAll:()=>[],createElement:()=>new Element(),addEventListener(){}},
    fetch:(_url,options)=>new Promise(resolve=>queue.push({resolve,options})),
  });
  vm.runInContext(fs.readFileSync('static/chat.js','utf8'),context);
  const first=context.ask('a first question');
  assert.equal(ids.question.disabled,true);
  assert.equal(ids.clear.disabled,false,'Reset stays available during a request');
  ids.clear.listeners.click();
  assert.equal(queue[0].options.signal.aborted,true);
  assert.equal(ids.question.disabled,false);
  assert.equal(ids.question.focused,true);
  assert.equal(ids['chat-form'].scrolled,true);
  assert.equal(ids.messages.children.length,1);
  assert.equal(ids.messages.children[0].phrase.dataset.i18n,'newWelcome');
  const second=context.ask('another question');
  queue[0].resolve({ok:true,json:async()=>({answer:'STALE REPLY',verses:[],sources:[]})});
  await first;
  assert.equal(ids.question.disabled,true,'An old response must not unlock a newer request');
  assert.equal(ids.messages.children.some(c=>c.firstChild?.textContent==='STALE REPLY'),false);
  queue[1].resolve({ok:true,json:async()=>({answer:'CURRENT REPLY',verses:[],sources:[]})});
  await second;
  assert.equal(ids.question.disabled,false);
  assert.equal(ids.messages.children.some(c=>c.firstChild?.textContent==='CURRENT REPLY'),true);
  ids.clear.listeners.click();
  assert.equal(ids.messages.children.length,1,'Completed replies are removed by reset');
  assert.equal(ids.question.value,'');
  console.log('Chat reset, cancellation, stale replies, and input focus: passed');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
