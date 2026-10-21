'use strict';
const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name=editor-token]').content;
const labels = {quest:'任務',friendly:'味方艦',enemy:'敵艦'};
const periods = {'1':'日次','2':'週次','3':'月次','4':'単発','5':'四半期・その他',...Object.fromEntries(Array.from({length:12},(_,i)=>[101+i,`年次（${i+1}月開始）`]))};
const events = {battle:'戦闘',practice:'演習',sink:'敵艦撃沈',mission:'遠征成功',sortie:'出撃',sVictory:'S勝利',boss:'ボス到達',bossVictory:'ボス勝利',repair:'入渠',supply:'補給',develop:'開発',build:'建造',scrapShip:'艦解体',improve:'装備改修',discardOperation:'廃棄操作',discardId:'指定装備廃棄',discardType:'指定カテゴリ廃棄',modernize:'近代化改修'};
const kinds = {bossBattle:'ボス戦',nodeBattle:'指定マス戦闘',reachNode:'指定マス到達',practice:'演習',mission:'遠征成功',discard:'装備廃棄'};
let data, model, dirty=false, rawDirty=false, previewToken=null;
const element = (tag,text,cls) => {const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
const row = () => element('div',undefined,'row');
function button(text,action,cls='quiet'){const b=element('button',text,cls);b.type='button';b.addEventListener('click',action);return b;}
function message(id,text){$(id).textContent=text||'';$(id).hidden=!text;}
function mark(){dirty=true;message('notice','');}
function number(text){return text===''?null:Number(text);}
function ids(text){return text.trim()===''?[]:text.split(/[,、\s]+/).filter(Boolean).map(Number);}
function input(label,value,change,{type='text',min,max,placeholder,help}={}){
 const l=element('label',label),c=element(type==='textarea'?'textarea':'input');
 if(type!=='textarea')c.type=type;else c.rows=3;
 c.value=value??'';if(min!==undefined)c.min=min;if(max!==undefined)c.max=max;if(placeholder)c.placeholder=placeholder;
 c.addEventListener('input',()=>{change(type==='number'?number(c.value):c.value);mark();});l.append(c);
 if(help)l.append(element('span',help,'help'));return l;
}
function select(label,value,choices,change){
 const l=element('label',label),c=element('select');
 if(!(String(value) in choices))c.append(new Option(`未設定・未対応 (${value??'空'})`,String(value??'')));
 for(const [v,t] of Object.entries(choices))c.append(new Option(t,v));c.value=String(value??'');
 c.addEventListener('change',()=>{change(c.value);mark();});l.append(c);return l;
}
function checkbox(label,checked,change){const l=element('label',undefined,'check'),c=element('input');c.type='checkbox';c.checked=checked;c.addEventListener('change',()=>{change(c.checked);mark();});l.append(c,document.createTextNode(label));return l;}
function csv(label,value,change,help){return input(label,Array.isArray(value)?value.join(', '):'',v=>change(ids(v)),{placeholder:'IDをカンマ区切りで指定',help});}
function choices(group){return data.choices?.groups[group]||{};}
function namedChoice(label,value,options,change,{optional=false,disabled=false}={}){
 const wrap=element('div',undefined,'named-choice'),l=element('label',label),filter=element('input'),c=element('select');
 filter.type='search';filter.placeholder='表示名・IDで検索';filter.setAttribute('aria-label',label+'を検索');c.setAttribute('aria-label',label);
 let selected=value===undefined||value===null?'':String(value);
 const match=s=>s.normalize('NFKC').toLocaleLowerCase();
 function draw(){
  c.replaceChildren(new Option(optional?'指定なし':'選択してください',''));
  if(selected!==''&&!(selected in options))c.append(new Option(`未収録ID [${selected}]`,selected));
  const query=match(filter.value);
  for(const [id,name] of Object.entries(options))if(id===selected||match(name+' '+id).includes(query))c.append(new Option(`${name} [${id}]`,id));
  c.value=selected;
 }
 filter.addEventListener('input',draw);c.addEventListener('change',()=>{selected=c.value;change(number(selected));mark();});
 l.append(filter,c);wrap.append(l);draw();
 if(disabled){filter.disabled=true;c.disabled=true;}else{
  const d=element('details',undefined,'manual-id');d.append(element('summary','未収録IDを入力'));
  d.append(input(label+'の未収録ID',selected,v=>{selected=v===null?'':String(v);draw();change(v);},{type:'number',min:0,max:100000}));wrap.append(d);
 }
 wrap.selectControl=c;return wrap;
}
function namedList(label,values,group,change,{allowZero=true}={}){
 const wrap=element('div',undefined,'named-list');wrap.append(element('p',label,'list-label'));
 let current=[...(values||[])];const body=element('div');wrap.append(body);
 const options=Object.fromEntries(Object.entries(choices(group)).filter(([k])=>allowZero||k!=='0'));
 function draw(){body.replaceChildren();current.forEach((value,i)=>{const r=row();r.append(namedChoice(`${label} ${i+1}`,value,options,v=>{current[i]=v;change([...current]);}),button('削除',()=>{current.splice(i,1);change([...current]);mark();draw();},'quiet remove'));body.append(r);});}
 wrap.append(button('＋ '+label+'を追加',()=>{current.push(null);change([...current]);mark();draw();}));draw();return wrap;
}
function choiceStatus(){const s=data.choices?.status||{};$('choice-status').textContent=s.warning|| (s.cached?'名称データ取得：'+new Date(s.fetchedAt).toLocaleString('ja-JP',{timeZone:'Asia/Tokyo',hour12:false})+' JST':'配信リソース内の名称を使用中。更新すると日本語の艦名等を補完できます。');}
function section(title){const s=element('section',undefined,'card'),h=element('div',undefined,'section-head');h.append(element('h3',title));s.append(h);return s;}
async function api(path,value){
 const response=await fetch(path,{method:value===undefined?'GET':'POST',headers:{'X-Editor-Token':token,...(value===undefined?{}:{'Content-Type':'application/json'})},...(value===undefined?{}:{body:JSON.stringify(value)})});
 const result=await response.json();if(!response.ok)throw Error(result.error||'処理に失敗しました');return result;
}
function guard(){return !dirty||window.confirm('保存していない入力を破棄しますか？');}
async function refresh(reset=true){
 data=await api('/api/bootstrap');choiceStatus();$('recovery').hidden=!data.pending;if(reset)newRecord(model?.kind||'quest');else renderList();
}
function renderList(){
 const list=$('records');list.replaceChildren();const query=$('search').value.toLocaleLowerCase();
 const found=data.lists[model.kind].filter(r=>`${r.id} ${r.name}`.toLocaleLowerCase().includes(query));
 $('count').textContent=`${found.length} / ${data.lists[model.kind].length} 件`;
 found.forEach(r=>{const b=button('',async()=>{if(!guard())return;try{const record=await api(`/api/record?kind=${model.kind}&id=${r.id}`);model={...record,mode:'edit',originalId:record.id,note:''};render();}catch(e){message('error',e.message);}},model.id===r.id?'selected':'');b.setAttribute('aria-label',`[${r.id}] ${r.name||labels[model.kind]}`);b.append(element('span',`ID ${r.id}`,'id'),element('span',r.name||`${labels[model.kind]} #${r.id}`));list.append(b);});
}
function newRecord(kind){
 model={kind,mode:'new',id:null,originalId:null,revision:data.revision,name:'',note:'',tracking:'catalog',after:kind==='quest'?{quest:{name:'',description:'',explanation:'',period:4,tasks:[]},native:null}:kind==='friendly'?{growth:[null,0,9999,9999,0,9999,9999]}:{hp:null,slots:null}};render();
}
function render(){
 dirty=false;rawDirty=false;message('error','');message('notice','');$('fields').replaceChildren();$('identity-field').replaceChildren();
 if(model.kind==='quest'){
  const f=input('ゲーム内部ID（必須）',model.id,v=>model.id=v,{type:'number',min:1,max:100000});f.querySelector('input').id='record-id';f.querySelector('input').required=true;f.querySelector('input').disabled=model.mode==='edit';$('identity-field').append(f);
 }else{
  const options=Object.fromEntries(Object.entries(choices('ships')).filter(([id])=>model.kind==='friendly'?Number(id)>0&&Number(id)<1500:Number(id)>=1500));
  const f=namedChoice('艦名（内部ID）',model.id,options,v=>{const old=model.id;model.id=v;if(options[v]&&(!$('record-name').value||$('record-name').value===options[old]))$('record-name').value=options[v];},{disabled:model.mode==='edit'});f.selectControl.id='record-id';f.selectControl.required=true;$('identity-field').append(f);
 }
 $('record-name').value=model.kind==='quest'?model.after.quest.name||'':model.name||'';$('record-name').required=model.kind==='quest';$('note').value=model.note||'';
 $('name-label').firstChild.textContent=model.kind==='quest'?'任務名（必須）':'艦名メモ（任意・編集ツールの一覧用）';
 $('form-heading').textContent=`${labels[model.kind]}を${model.mode==='new'?'追加':'編集'}`;$('mode').textContent=model.mode==='new'?'新規追加':`登録済み · ID ${model.id}`;
 $('list-heading').textContent=`${labels[model.kind]}一覧`;document.querySelectorAll('nav button').forEach(b=>b.classList.toggle('active',b.dataset.kind===model.kind));
 if(model.kind==='quest')questForm();else if(model.kind==='friendly')friendlyForm();else enemyForm();
 advancedForm();renderList();
}
function questForm(){
 const q=model.after.quest,n=model.after.native;
 if(!('period' in q))q.period=n?.period??4;
 const info=section('基本情報'),r=row();r.append(select('任務周期',q.period,periods,v=>q.period=Number(v)));
 const fleets=element('div',undefined,'checks');for(let i=1;i<=4;i++)fleets.append(checkbox(`第${i}艦隊`,q.fleetIds?.includes(i)||false,v=>{const s=new Set(q.fleetIds||[]);v?s.add(i):s.delete(i);if(s.size)q.fleetIds=[...s].sort();else delete q.fleetIds;}));
 const f=element('div');f.append(element('p','対象艦隊（未選択なら限定しない）','hint'),fleets);
 info.append(r,input('任務説明',q.description||'',v=>q.description=v,{type:'textarea'}),input('補足説明',q.explanation||'',v=>q.explanation=v,{type:'textarea'}),f);$('fields').append(info);
 info.append(input('確認済みの詳細条件',q.conditionsText||'',v=>q.conditionsText=v,{type:'textarea',help:'所持資材・装備・実施順序など、カウンタだけでは表せない条件も記載します。説明文からの自動カウントは行いません。'}));
 const counter=section('達成条件'),mode=n?'native':q.tasks?.length?'catalog':model.tracking||'none';model.tracking=mode;
 if(!n)counter.append(select('カウンタの集計期間',q.counterPeriod||'',{'':'任務周期と同じ',1:'当日内（AM5:00更新）',2:'当週内',3:'当月内'},v=>{if(v)q.counterPeriod=Number(v);else delete q.counterPeriod;}));
 counter.append(select('カウンタ形式',mode,{catalog:'海域・演習・遠征・廃棄の条件',native:'観測イベント（撃沈・補給・工廠など）',none:'カウンタなし（説明・編成条件のみ）'},v=>{model.tracking=v;q.tasks=[];if(v==='native')delete q.counterPeriod;model.after.native=v==='native'?{name:q.name,period:q.period,tasks:[]}:null;render();mark();}));
 counter.append(element('p','複数の条件はすべて満たす必要があります。カウンタに含められない条件は任務説明にも記載してください。','hint'));
 const body=element('div');body.id='condition-list';counter.append(body);$('fields').append(counter);renderConditions(counter);
 const formation=section('編成条件'),wrap=element('div');
 formation.append(checkbox('編成条件を指定する',!!q.formation,enabled=>{if(enabled)q.formation={op:'count',min:1,selector:{op:'type',values:[2]}};else delete q.formation;draw();}));formation.append(wrap);
 function draw(){wrap.replaceChildren();if(q.formation)wrap.append(ruleEditor(q.formation,v=>q.formation=v,false,0));}draw();$('fields').append(formation);
}
function taskDefault(kind,native){
 if(native)return {event:kind,target:1,ids:[],rank:'E',materialTypes:[],required:0};
 const t={kind,target:1};if(['bossBattle','nodeBattle','reachNode'].includes(kind))t.map={area:1,number:1};if(['bossBattle','nodeBattle','practice'].includes(kind))t.rank='S';if(['nodeBattle','reachNode'].includes(kind))t.cells=[1];if(kind==='mission')t.missionIds=[0];if(kind==='discard'){t.selectBy='id';t.ids=[1];}return t;
}
function renderConditions(sectionNode){
 const list=$('condition-list');list.replaceChildren();const native=model.tracking==='native',none=model.tracking==='none';
 if(none){list.append(element('p','独自の進捗加算は行いません。ゲームから届く達成状態を利用します。','hint'));return;}
 const tasks=native?model.after.native.tasks:(model.after.quest.tasks??=[]),items=element('div',undefined,'task-list');
 tasks.forEach((t,i)=>{
  const box=element('div',undefined,'task'),head=row();head.append(select('条件種別',native?t.event:t.kind,native?events:kinds,v=>{tasks[i]=taskDefault(v,native);renderConditions(sectionNode);}));
  head.append(input('必要回数・個数',t.target,v=>t.target=v,{type:'number',min:1,max:100000}));head.append(button('削除',()=>{tasks.splice(i,1);mark();renderConditions(sectionNode);},'remove quiet'));box.append(head);
  const r=row();
  if(native){
   const group={sink:'types',mission:'missions',discardId:'equipment',discardType:'categories',modernize:'types',battle:'maps'}[t.event];
   r.append(select('勝利評価',t.rank||'E',{E:'指定なし',D:'D以上',C:'C以上',B:'B以上',A:'A以上',S:'S'},v=>t.rank=v));box.append(r);
   box.append(group?namedList('対象',t.ids||[],group,v=>t.ids=v):csv('対象ID',t.ids||[],v=>t.ids=v,'対象IDの意味は観測イベントの仕様に従います。'));
   box.append(namedList('素材艦の艦種',t.materialTypes||[],'types',v=>t.materialTypes=v),input('素材艦の必要隻数（近代化改修用）',t.required??0,v=>t.required=v,{type:'number',min:0,max:100}),element('p','素材艦の艦種・必要隻数は近代化改修の素材条件です。資材の種類・消費量ではありません。','hint'));
  }else{
   if(t.map){r.append(input('海域方面',t.map.area,v=>t.map.area=v,{type:'number',min:1,max:1000}),input('海域番号',t.map.number,v=>t.map.number=v,{type:'number',min:1,max:1000}));}
   if('rank' in t)r.append(select('必要な勝利評価',t.rank,{any:'指定なし',battle:'戦闘実施',D:'D以上',C:'C以上',B:'B以上',A:'A以上',S:'S',SS:'完全S'},v=>t.rank=v));
   if('cells' in t)r.append(csv('マス内部ID',t.cells,v=>t.cells=v));
   if('missionIds' in t)box.append(namedList('遠征',t.missionIds,'missions',v=>t.missionIds=v));
   if(t.kind==='discard'){
    r.append(select('装備の指定方法',t.selectBy,{id:'装備ID',category:'装備カテゴリ',cardType:'カード分類',icon:'アイコン分類'},v=>{t.selectBy=v;renderConditions(sectionNode);}));
    const group={id:'equipment',category:'categories',cardType:'cards',icon:'icons'}[t.selectBy];box.append(namedChoice('対象装備・分類',t.ids?.[0],choices(group),v=>t.ids=[v]));
   }
   if(!(t.kind in kinds))box.append(element('p','この条件は通常フォームでは未対応です。JSONを確認してください。','hint'));
   box.append(r);
  }
  items.append(box);
 });
 list.append(items,button('＋ 条件を追加',()=>{tasks.push(taskDefault(native?'battle':'bossBattle',native));mark();renderConditions(sectionNode);}));
}
function ruleDefault(op,selector){
 const s={op:'type',values:[2]},c={op:'count',min:1,selector:s};
 if(op==='all'||op==='any')return {op,conditions:[selector?s:c]};
 if(op==='not')return {op,condition:s};if(op==='count')return c;
 if(op==='candidates')return {op,min:1,candidates:[{positions:[1,2,3,4,5,6,7],countAll:false,selector:s}]};
 if(['type','class','nationality','hull'].includes(op))return {op,values:[op==='type'?2:1],...(op==='hull'?{minimumStage:0}:{})};
 if(op==='ship')return {op,id:1,remodel:'family'};if(op==='level')return {op,min:1};return {op:'always'};
}
function ruleEditor(rule,setRule,selector,depth){
 const wrap=element('div',undefined,'condition');if(depth>=15){wrap.append(element('p','深い条件はJSONで編集してください。'));return wrap;}
 const options=selector?{all:'すべて一致',any:'いずれか一致',not:'該当しない',always:'全艦',type:'艦種',class:'艦型',nationality:'国籍',hull:'艦識別・改装段階',level:'レベル',ship:'指定艦'}:{all:'すべての条件',any:'いずれかの条件',count:'隻数条件',candidates:'指定候補の一致数'};
 let current=rule;const header=row(),body=element('div',undefined,'condition-body');header.append(select(selector?'艦の選択条件':'編成の条件',current.op,options,op=>{current=ruleDefault(op,selector);setRule(current);draw();}));wrap.append(header,body);
 function draw(){
  body.replaceChildren();const q=current,r=row();
  if(q.op==='all'||q.op==='any'){
   q.conditions.forEach((c,i)=>{const line=element('div');line.append(ruleEditor(c,v=>q.conditions[i]=v,selector,depth+1),button('この条件を削除',()=>{q.conditions.splice(i,1);mark();draw();},'quiet remove'));body.append(line);});
   body.append(button('＋ 子条件を追加',()=>{q.conditions.push(ruleDefault(selector?'type':'count',selector));mark();draw();}));
  }else if(q.op==='not')body.append(ruleEditor(q.condition,v=>q.condition=v,true,depth+1));
  else if(q.op==='count'){
   r.append(input('最小隻数',q.min,v=>q.min=v,{type:'number',min:0,max:100}),input('最大隻数（空欄＝上限なし）',q.max,v=>{if(v===null)delete q.max;else q.max=v;},{type:'number',min:0,max:100}),csv('位置（空欄＝全艦）',q.positions||[],v=>{if(v.length)q.positions=v;else delete q.positions;},'1＝旗艦、2～7＝随伴'));
   body.append(r,ruleEditor(q.selector,v=>q.selector=v,true,depth+1));
  }else if(q.op==='candidates'){
   body.append(input('必要な一致数',q.min,v=>q.min=v,{type:'number',min:0,max:100}));
   q.candidates.forEach((c,i)=>{const line=element('div',undefined,'task');line.append(csv('判定する位置',c.positions,v=>c.positions=v),checkbox('該当する実隻数を数える',c.countAll,v=>c.countAll=v),ruleEditor(c.selector,v=>c.selector=v,true,depth+1),button('候補を削除',()=>{q.candidates.splice(i,1);mark();draw();},'quiet remove'));body.append(line);});
   body.append(button('＋ 候補を追加',()=>{q.candidates.push({positions:[1,2,3,4,5,6,7],countAll:false,selector:{op:'type',values:[2]}});mark();draw();}));
  }else if(['type','class','nationality','hull'].includes(q.op)){
   const groups={type:'types',class:'classes',nationality:'nationalities',hull:'hulls'},names={type:'艦種',class:'艦型',nationality:'国籍',hull:'艦識別'};
   body.append(namedList(names[q.op],q.values,groups[q.op],v=>q.values=v,{allowZero:false}));
   if(q.op==='hull')body.append(input('最低改装段階',q.minimumStage,v=>q.minimumStage=v,{type:'number',min:0,max:9}));
  }else if(q.op==='level')body.append(input('最低レベル',q.min,v=>q.min=v,{type:'number',min:0,max:1000}));
  else if(q.op==='ship'){
   r.append(namedChoice('艦名',q.id,choices('ships'),v=>q.id=v),namedChoice('艦型（任意）',q.class,choices('classes'),v=>{if(v===null)delete q.class;else q.class=v;},{optional:true}),select('改装の扱い',q.remodel,{family:'改装系統',atLeast:'指定形態以降',exact:'指定形態のみ'},v=>q.remodel=v));body.append(r);
  }else if(q.op!=='always')body.append(element('p','未対応の条件は省略せず、JSONで確認してください。','hint'));
 }
 draw();return wrap;
}
function friendlyForm(){
 const s=section('回避・対潜の成長値');s.append(element('p','艦名・艦種・改装先などの基本情報は、アプリがゲームマスターから取得します。この画面では補完用の成長値を編集します。','hint'));
 for(const [title,index] of [['回避',1],['対潜',4]]){
  const f=element('fieldset'),leg=element('legend',title),wrap=row();f.append(leg);s.append(f);
  const draw=()=>{wrap.replaceChildren();const unknown=model.after.growth.slice(index,index+3).join(',')==='0,9999,9999';if(!unknown)for(const [i,label] of ['初期値・下限','初期値・上限','Lv99値'].entries())wrap.append(input(label,model.after.growth[index+i],v=>model.after.growth[index+i]=v,{type:'number',min:0,max:9998}));};
  f.append(checkbox('値が未確定',model.after.growth[index+1]===9999,v=>{model.after.growth.splice(index,3,...(v?[0,9999,9999]:[0,0,0]));draw();}));f.append(wrap);draw();
 }
 $('fields').append(s);
}
function enemyForm(){
 const s=section('初期耐久・個別搭載数');s.append(input('初期耐久（未取得なら空欄）',model.after.hp,v=>model.after.hp=v,{type:'number',min:1,max:100000}),element('p','総搭載数から各スロットへ分配しないでください。既存の値は空欄にして削除できません。','hint'));
 const slots=row();const draw=()=>{slots.replaceChildren();if(model.after.slots)for(let i=0;i<5;i++)slots.append(input(`スロット${i+1}`,model.after.slots[i],v=>model.after.slots[i]=v,{type:'number',min:0,max:10000}));};
 s.append(checkbox('スロット別搭載数を設定する',model.after.slots!==null,v=>{model.after.slots=v?[0,0,0,0,0]:null;draw();}),slots);draw();$('fields').append(s);
}
function collect(){
 model.id=number($('record-id').value);model.name=$('record-name').value;model.note=$('note').value;
 if(model.kind==='quest'){model.after.quest.name=model.name;if(model.after.native){model.after.native.name=model.name;model.after.native.period=model.after.quest.period;}}
 else if(model.kind==='friendly')model.after.growth[0]=model.id;
 return model;
}
function advancedForm(){
 const d=element('details'),summary=element('summary','詳細JSON・互換情報'),area=element('textarea',undefined,'json');area.id='raw-json';area.setAttribute('aria-label','編集内容JSON');area.spellcheck=false;
 area.value=JSON.stringify(model.after,null,2);area.addEventListener('input',()=>{rawDirty=true;mark();});
 const controls=element('div',undefined,'raw-controls');controls.append(button('フォームのJSONを表示',()=>{collect();area.value=JSON.stringify(model.after,null,2);rawDirty=false;}),button('JSONをフォームに反映',()=>{try{const value=JSON.parse(area.value);if(model.kind==='quest'&&(!value.quest||!Array.isArray(value.quest.tasks)))throw Error('questとtasks配列が必要です');if(model.kind==='friendly'&&!Array.isArray(value.growth))throw Error('growth配列が必要です');collect();model.after=value;if(model.kind==='quest')model.tracking=value.native?'native':value.quest.tasks.length?'catalog':'none';render();mark();}catch(e){message('error',e.message);}}));
 d.append(summary,element('p','通常はフォームで入力できます。旧カウンタの移行キー・ハッシュは変更しないでください。JSONを編集したら「フォームに反映」を押してください。','hint'),controls,area);$('fields').append(d);
}
$('record-name').addEventListener('input',mark);$('note').addEventListener('input',mark);$('search').addEventListener('input',renderList);
$('refresh-choices').addEventListener('click',async()=>{if(rawDirty){message('error','先にJSONをフォームに反映してください。');return;}const b=$('refresh-choices');b.disabled=true;const wasDirty=dirty;try{collect();await api('/api/choices/refresh',{});data=await api('/api/bootstrap');choiceStatus();render();dirty=wasDirty;message('notice','名称の選択肢を更新しました。マスターの編集内容は保持しています。');}catch(e){message('error','名称の取得に失敗しました。保存済みの候補を使います。');}finally{b.disabled=false;}});
document.querySelectorAll('nav button').forEach(b=>b.addEventListener('click',()=>{if(guard()){$('search').value='';newRecord(b.dataset.kind);}}));
$('new').addEventListener('click',()=>{if(guard())newRecord(model.kind);});$('reload').addEventListener('click',async()=>{if(!guard())return;try{await refresh();}catch(e){message('error',e.message);}});
$('form').addEventListener('submit',async event=>{event.preventDefault();message('error','');try{if(rawDirty)throw Error('変更したJSONをフォームに反映してから確認してください。');const p=await api('/api/preview',collect());previewToken=p.token;$('summary').textContent=`[${p.id}] ${p.name||labels[model.kind]}`;$('files').textContent='保存対象：'+p.files.join('、');$('diff').textContent=p.diff;message('save-error','');$('confirmation').showModal();}catch(e){message('error',e.message);}});
$('cancel').addEventListener('click',()=>$('confirmation').close());
$('save').addEventListener('click',async()=>{const b=$('save');b.disabled=true;try{const result=await api('/api/save',{token:previewToken});$('confirmation').close();dirty=false;const kind=model.kind,id=model.id;await refresh(false);const r=await api(`/api/record?kind=${kind}&id=${id}`);model={...r,mode:'edit',originalId:id,note:''};render();message('notice',result.message);}catch(e){message('save-error',e.message);}finally{b.disabled=false;}});
$('recover').addEventListener('click',async()=>{if(!window.confirm('中断した保存を元に戻しますか？'))return;try{const result=await api('/api/recover',{});dirty=false;await refresh();message('notice',result.message);}catch(e){message('error',e.message);}});
window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
refresh().catch(e=>message('error',e.message));
