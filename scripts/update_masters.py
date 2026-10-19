"""Windows/PC Wiki master updater: fetch -> plan -> human review -> apply.

Python 3.10+, standard library only. Never contacts a game server or publishes a Release.
"""
import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, request, robotparser
from urllib.parse import quote, urlsplit, urlunsplit

from wiki_readers import clean, draft_counter, draft_formation, identity, parse

ROOT = Path(__file__).resolve().parents[1]
HOSTS = {'wikiwiki.jp', 'en.kancollewiki.net'}
FILES = ['quest-catalog.json', 'recurring-quests.json', 'ship-growth.json', 'enemy-ship-hp.json', 'enemy-aircraft-slots.json']
EVENTS = {'battle','practice','sink','mission','sortie','sVictory','boss','bossVictory','repair','supply','develop','build','scrapShip','improve','discardOperation','discardId','discardType','modernize'}
PERIODS = {1,2,3,4,5,*range(101,113)}


def digest(value): return hashlib.sha256(value).hexdigest()
def stamp(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def load(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def encoded(value): return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')


def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name+'.tmp')
    with temp.open('wb') as stream: stream.write(data); stream.flush(); os.fsync(stream.fileno())
    os.replace(temp, path)


def url(value):
    p=urlsplit(value)
    if p.scheme!='https' or p.hostname not in HOSTS or p.username or p.password or p.port:
        raise ValueError('WikiのHTTPS URLだけ指定できます')
    if p.hostname=='wikiwiki.jp' and not (p.path.startswith('/kancolle/') or p.path=='/robots.txt'):
        raise ValueError('別のWikiは取得対象外です')
    return urlunsplit((p.scheme,p.netloc,quote(p.path,safe='/%:@'),quote(p.query,safe='=&%:+'),''))


class Redirects(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(req,fp,code,msg,headers,url(newurl))


class Fetcher:
    def __init__(self): self.opener=request.build_opener(Redirects()); self.last={}; self.robots={}; self.delay={}
    def get(self, target, limit=6*1024*1024):
        target=url(target); host=urlsplit(target).netloc
        time.sleep(max(0, self.delay.get(host,5)-(time.monotonic()-self.last.get(host,0))))
        self.last[host]=time.monotonic()
        req=request.Request(target,headers={'User-Agent':'n9aBrowserMasterUpdater/1.0 (manual review; public Wiki data only)'})
        with self.opener.open(req,timeout=30) as response:
            data=response.read(limit+1)
            if len(data)>limit: raise ValueError('ページが取得サイズ上限を超えています')
            return data
    def allowed(self, target):
        p=urlsplit(url(target)); host=p.netloc
        if host not in self.robots:
            robots_url=f'https://{host}/robots.txt'
            try: raw=self.get(robots_url,256*1024)
            except error.HTTPError as exc:
                if exc.code==404: raw=b''
                else: raise
            parser=robotparser.RobotFileParser(robots_url);parser.parse(raw.decode('utf-8').splitlines());self.robots[host]=parser
            self.delay[host]=max(5,parser.crawl_delay('n9aBrowserMasterUpdater') or 0)
        return self.robots[host].can_fetch('n9aBrowserMasterUpdater',url(target))


def config(path):
    value=load(path)
    if value.get('schema')!=1: raise ValueError('未対応の設定形式です')
    keys=[]
    for source in value['sources']:
        if not re.fullmatch(r'[a-z0-9_-]{1,80}',source['key']): raise ValueError('source keyが不正です')
        keys.append(source['key']);url(source['url'])
        if source['kind'] not in {'quests','friendly','enemies','links'}: raise ValueError('未対応のsource kindです')
    if len(keys)!=len(set(keys)) or len(keys)>80: raise ValueError('取得先の重複または件数上限です')
    return value


def fetch(cfg, work, refresh=False, imported=None):
    cache=work/'pages';cache.mkdir(parents=True,exist_ok=True)
    client=Fetcher(); results=[]; blocked=set()
    for source in cfg['sources']:
        if not source.get('enabled',True) and not (imported and imported[0]==source['key']): continue
        page=cache/(source['key']+'.html'); meta_path=cache/(source['key']+'.json')
        result=dict(key=source['key'],url=url(source['url']),ok=False)
        try:
            if imported and imported[0]==source['key']:
                raw=Path(imported[1]).read_bytes()
                if len(raw)>6*1024*1024: raise ValueError('保存ページが大きすぎます')
            elif imported: continue
            elif page.exists() and meta_path.exists() and not refresh and time.time()-page.stat().st_mtime<86400:
                meta=load(meta_path);raw=page.read_bytes()
                if meta['url']!=result['url'] or meta['sha256']!=digest(raw): raise ValueError('キャッシュが不一致です。--refreshで取得し直してください')
                result.update(ok=True,cached=True);results.append(result);print(source['key']+': cached',flush=True);continue
            else:
                if urlsplit(source['url']).hostname in blocked:raise ValueError('同一ホストのアクセス制限により今回は取得を中止しました')
                if not client.allowed(source['url']): raise ValueError('robots.txtで自動取得が許可されていません')
                raw=client.get(source['url'])
            raw.decode('utf-8-sig')
            atomic(page,raw);atomic(meta_path,encoded(dict(url=result['url'],sha256=digest(raw),fetchedAt=stamp(),imported=bool(imported))))
            result['ok']=True
        except Exception as exc:
            # Status/error categories only: never include response bodies or local file paths.
            result['error']=f'HTTP {exc.code}' if isinstance(exc,error.HTTPError) else str(exc) if isinstance(exc,ValueError) else type(exc).__name__
            if isinstance(exc,error.HTTPError) and exc.code in (429,503):blocked.add(urlsplit(source['url']).hostname)
        results.append(result)
        print(source['key']+': '+('OK' if result['ok'] else result['error']),flush=True)
    if imported and (work/'fetch-report.json').exists():
        keys={x['key'] for x in results}
        results=[x for x in load(work/'fetch-report.json')['sources'] if x['key'] not in keys]+results
    atomic(work/'fetch-report.json',encoded(dict(at=stamp(),sources=results)))
    print('取得成功:',sum(x['ok'] for x in results),'失敗:',sum(not x['ok'] for x in results))
    return sum(not x['ok'] for x in results)


def n(value, lo=0, hi=100000):
    if type(value) is not int or not lo<=value<=hi: raise ValueError(f'整数範囲が不正です ({lo}..{hi})')
    return value


def ints(value,lo=0,hi=100000):
    if not isinstance(value,list) or not 1<=len(value)<=100: raise ValueError('ID配列が不正です')
    for x in value:n(x,lo,hi)


def formation(q,depth=0,selector=False):
    if depth>=16 or not isinstance(q,dict): raise ValueError('編成条件の構造が不正です')
    op=q['op']
    fields={'all':{'conditions'},'any':{'conditions'},'not':{'condition'},'count':{'min','max','positions','selector'},
            'candidates':{'min','candidates'},'always':set(),'type':{'values'},'class':{'values'},'nationality':{'values'},
            'hull':{'values','minimumStage'},'level':{'min'},'ship':{'id','class','remodel'}}
    if op not in fields or set(q)-{'op'}-fields[op]:raise ValueError('未知の編成条件・項目です')
    if op in ('all','any'):
        if not isinstance(q['conditions'],list) or len(q['conditions'])>100: raise ValueError('編成条件が多すぎます')
        for c in q['conditions']:formation(c,depth+1,selector)
    elif op=='not' and selector:formation(q['condition'],depth+1,True)
    elif op=='count' and not selector:
        low=n(q['min'],0,100);n(q.get('max',100),low,100)
        if 'positions' in q:ints(q['positions'],1,7)
        formation(q['selector'],depth+1,True)
    elif op=='candidates' and not selector:
        n(q['min'],0,100)
        if len(q['candidates'])>100:raise ValueError('候補数が多すぎます')
        for c in q['candidates']:
            if set(c)-{'positions','countAll','selector'}:raise ValueError('未知の編成候補項目です')
            ints(c['positions'],1,7)
            if type(c['countAll']) is not bool:raise ValueError('countAllが不正です')
            formation(c['selector'],depth+1,True)
    elif op in ('type','class','nationality','hull') and selector:
        ints(q['values'])
        if op=='hull':n(q['minimumStage'],0,9)
    elif op=='level' and selector:n(q['min'],0,1000)
    elif op=='ship' and selector:
        n(q['id']);n(q.get('class',0))
        if q['remodel'] not in ('family','atLeast','exact'):raise ValueError('未対応の改装比較です')
    elif op=='always' and selector:pass
    else:raise ValueError('未対応の編成条件: '+str(op))


def validate_quest(q,native):
    if set(q)-{'name','description','explanation','tasks','formation','period','fleetIds','legacyCounterKeys','legacyDefinitionHash'}:raise ValueError('未知の任務項目です')
    for key in ('name','description','explanation'):
        if key in q and q[key] is not None and (not isinstance(q[key],str) or len(q[key])>20000):raise ValueError('文字列が不正です')
    if type(q.get('period')) is not int or q['period'] not in PERIODS:raise ValueError('任務周期を確認してください')
    if q.get('formation'):formation(q['formation'])
    if q.get('fleetIds'):ints(q['fleetIds'],1,4)
    tasks=q.get('tasks',[])
    if not isinstance(tasks,list) or len(tasks)>100:raise ValueError('達成条件が不正です')
    for task in tasks:
        k=task['kind'];n(task['target'],1)
        fields={'bossBattle':{'map','rank'},'nodeBattle':{'map','rank','cells'},'reachNode':{'map','cells'},
                'practice':{'rank'},'mission':{'missionIds'},'discard':{'selectBy','ids'}}
        if k not in fields or set(task)-{'kind','target'}-fields[k]:raise ValueError('未知の達成条件・項目です')
        if k in ('bossBattle','nodeBattle','reachNode'):
            if set(task['map'])!={'area','number'}:raise ValueError('未知の海域項目です')
            n(task['map']['area'],1,1000);n(task['map']['number'],1,1000)
        if k in ('bossBattle','nodeBattle','practice') and task['rank'] not in ('any','battle','D','C','B','A','S','SS'):raise ValueError('戦闘評価が不正です')
        if k in ('nodeBattle','reachNode'):ints(task['cells'])
        if k=='mission':ints(task['missionIds'])
        if k=='discard':
            ints(task['ids'],1)
            if len(task['ids'])!=1 or task['selectBy'] not in ('id','category','cardType','icon'):raise ValueError('廃棄条件が不正です')
        if k not in ('bossBattle','nodeBattle','reachNode','practice','mission','discard'):raise ValueError('未対応の達成条件: '+str(k))
    if native:
        if tasks:raise ValueError('tasksとnativeはどちらか一方を指定してください')
        if set(native)-{'period','name','tasks'}:raise ValueError('未知の観測カウンタ項目です')
        if not 1<=len(native['tasks'])<=100 or type(native['period']) is not int or native['period'] not in PERIODS:raise ValueError('観測カウンタが不正です')
        if not isinstance(native.get('name'),str) or not 1<=len(native['name'])<=20000:raise ValueError('任務名が不正です')
        for t in native['tasks']:
            if set(t)-{'event','target','ids','rank','materialTypes','required'}:raise ValueError('未知のトリガー項目です')
            for field,default in (('ids',[]),('rank','E'),('materialTypes',[]),('required',0)):
                t.setdefault(field,copy.deepcopy(default))
            if t['event'] not in EVENTS:raise ValueError('未対応のトリガーです')
            n(t['target'],1)
            if t.get('rank','E') not in ('S','A','B','C','D','E'):raise ValueError('戦闘評価が不正です')
            for field in ('ids','materialTypes'):
                if not isinstance(t.get(field,[]),list) or len(t.get(field,[]))>100:raise ValueError('ID配列が不正です')
                for x in t.get(field,[]):n(x)
            n(t.get('required',0),0,100)
            if t['event'] in ('sink','discardId','discardType') and not t.get('ids'):raise ValueError('艦種・装備の対象IDが必要です')
            if (q.get('formation') or q.get('fleetIds')) and t['event'] not in ('battle','practice'):
                raise ValueError('このトリガーと編成・艦隊条件の組合せは自動適用対象外です')
        if native['period']!=q['period']:raise ValueError('周期が一致しません')
    if not tasks and not native:raise ValueError('対応済みの達成条件を指定してください')


def baseline(root): return {name:digest((root/'data'/name).read_bytes()) for name in FILES}
def state(root):return {name:load(root/'data'/name) for name in FILES}


def discover_ships(cfg,work,master_path,root,all_ships=False,limit=20):
    master=load(master_path)
    if isinstance(master,dict) and 'api_data' in master:master=master['api_data']
    if not isinstance(master,dict) or not isinstance(master.get('api_mst_ship'),list):raise ValueError('api_mst_shipを含む公開マスターJSONを指定してください')
    discovered=load(work/'discovered-pages.json');pages={}
    for page in discovered:pages.setdefault(identity(page['name']),set()).add(url(page['url']))
    existing={r[0] for r in load(root/'data/ship-growth.json')};known={s.get('shipId') for s in cfg['sources']}
    new=copy.deepcopy(cfg);missing=[];added=0
    for ship in master['api_mst_ship']:
        id=n(ship['api_id'],1);name=ship['api_name']
        if id>=1500 or id in known or not all_ships and id in existing:continue
        matches=pages.get(identity(name),set())
        if len(matches)!=1:missing.append(dict(id=id,name=name,reason='Wikiページ未発見または複数候補'));continue
        if added>=limit:missing.append(dict(id=id,name=name,reason='今回の追加上限'));continue
        new['sources'].append(dict(key='ship-'+str(id),kind='friendly',name=name,shipId=id,url=next(iter(matches)),enabled=True));added+=1
    atomic(work/'ship-sources.json',encoded(new));atomic(work/'ship-mapping-issues.json',encoded(missing))
    print('艦ページ設定候補:',added,'件。ship-sources.jsonを確認して--configに指定してください。未解決:',len(missing))


def plan(cfg,work,root):
    current=state(root); catalog=current['quest-catalog.json'];quests=catalog['quests'];native=current['recurring-quests.json']
    names={}
    for id,q in quests.items():
        if q.get('name'):names.setdefault(identity(q['name']),[]).append(int(id))
    proposals=[];issues=[];discovered=[]; bindings=cfg.get('bindings',{})
    report=load(work/'fetch-report.json') if (work/'fetch-report.json').exists() else {'sources':[]}
    failures={x['key'] for x in report['sources'] if not x['ok']}
    for source in cfg['sources']:
        page=work/'pages'/(source['key']+'.html');meta=work/'pages'/(source['key']+'.json')
        if source['key'] in failures or not page.exists() or not meta.exists():
            if source.get('enabled',True):issues.append(dict(source=source['key'],reason='未取得・取得失敗。旧キャッシュは候補に流用しません'))
            continue
        raw=page.read_bytes();evidence=load(meta)
        if digest(raw)!=evidence['sha256'] or url(source['url'])!=evidence['url']:raise ValueError('保存ページの整合性が不正です')
        records,warnings=parse(raw.decode('utf-8-sig'),source)
        issues.extend(dict(source=source['key'],reason=x) for x in warnings)
        for record in records:
            if record['kind']=='link':discovered.append(record);continue
            id=record.get('id');before=None;notes=[];kind=record['kind']
            if kind=='quest':
                matches=names.get(identity(record['name']),[])
                id=bindings.get('quests',{}).get(source['key']+'/'+record['wikiId'],bindings.get('quests',{}).get(record['wikiId']))
                if id is None and len(matches)==1:id=matches[0]
                if id is None:notes.append('ゲーム内部の任務IDが未確定。Wiki番号から推測しません。新規IDを指定するかbindingsへ登録してplanを再生成してください。')
                before=copy.deepcopy(quests.get(str(id)))
                q=copy.deepcopy(before) if before else {'tasks':[]}
                q.update(name=record['name'],description=record['description'])
                if 'period' not in q:
                    code=record['wikiId'];q['period']=next((v for suffix,v in [('d',1),('w',2),('m',3),('q',5)] if re.match('[A-Z]'+suffix+r'\d',code)),4 if re.match(r'[A-Z]\d',code) else None)
                counter=draft_counter(record['description']);nq=copy.deepcopy(native.get(str(id)))
                if counter and counter['format']=='catalog':q['tasks']=counter['tasks'];nq=None
                elif counter:
                    nq=dict(period=q['period'],name=q['name'],tasks=counter['tasks']);q['tasks']=[]
                else:notes.append('達成条件は全文を確認し、既知のtasksまたはnativeへ入力してください。')
                f=draft_formation(record['description'])
                if f and not q.get('formation'):q['formation']=f
                notes.append('自動抽出は候補です。艦隊・編成・回数・各海域・勝利評価など、Wiki本文全体との一致を必ず確認してください。')
                after=dict(quest=q,native=nq)
                if before==q and native.get(str(id))==nq:continue
            elif kind=='friendly':
                if id is None:id=bindings.get('ships',{}).get(record['name'])
                growth=next((r for r in current['ship-growth.json'] if r[0]==id),None);before=copy.deepcopy(growth)
                row=copy.deepcopy(growth) if growth else [id,0,9999,9999,0,9999,9999]
                for key,index in [('evasion',1),('asw',4)]:
                    if record.get(key):row[index:index+3]=record[key]
                    else:notes.append(key+'が不明。既存値を維持し、新規艦では未確定値とします。')
                if id is None:notes.append('内部艦IDが未確定です。図鑑番号は使用しません。')
                after=dict(growth=row)
                if row==growth:continue
            else:
                before=dict(hp=current['enemy-ship-hp.json']['hp'].get(str(id)),slots=current['enemy-aircraft-slots.json'].get(str(id)))
                after=copy.deepcopy(before)
                if record.get('hp'):after['hp']=record['hp']
                else:notes.append('耐久が不明・複数値です。既存値を維持します。')
                if source.get('slotCounts',{}).get(str(id)) is not None:after['slots']=source['slotCounts'][str(id)]
                if after==before:continue
            proposals.append(dict(key=source['key']+'/'+str(record.get('wikiId',id)),kind=kind,id=id,name=record['name'],approved=False,
                                  before=before,beforeNative=copy.deepcopy(native.get(str(id))) if kind=='quest' else None,
                                  after=after,notes=notes,evidence=evidence))
    result=dict(schema=1,createdAt=stamp(),base=baseline(root),proposals=proposals,issues=issues)
    atomic(work/'review.json',encoded(result));atomic(work/'discovered-pages.json',encoded(discovered))
    lines=['# マスターデータ更新候補','',f'候補: {len(proposals)}件 / 取得・解析の確認事項: {len(issues)}件','',
           'review.jsonのafterを本文と照合し、適用する候補だけapprovedをtrueにしてください。未確定IDは図鑑番号から推測しないでください。','']
    for p in proposals:
        lines += [f"## {p['key']} {p['name']}",f"内部ID: {p['id']}",f"出典: {p['evidence']['url']}"]+['- '+n for n in p['notes']]+['']
    for issue in issues:lines.append('- '+issue['source']+': '+issue['reason'])
    atomic(work/'report.md',('\n'.join(lines)+'\n').encode('utf-8'))
    print('確認用ファイル: review.json / report.md / discovered-pages.json; 候補:',len(proposals))


def prepare(plan_data,root):
    if plan_data.get('schema')!=1 or plan_data['base']!=baseline(root):raise ValueError('元データが変更されています。planを再生成してください')
    data=state(root);seen=set();applied=[]
    for p in plan_data['proposals']:
        if p.get('approved') is not True:continue
        kind=p['kind'];id=n(p['id'],1);key=str(id);after=p['after']
        if (kind,id) in seen:raise ValueError('同一IDの候補が複数あります。一つに統合してから適用してください')
        seen.add((kind,id))
        if kind=='quest':
            old=data['quest-catalog.json']['quests'].get(key)
            if old!=p['before'] or data['recurring-quests.json'].get(key)!=p.get('beforeNative'):raise ValueError('任務IDと比較元が一致しません。bindingsを設定してplanを再生成してください')
            q=after['quest'];nq=after.get('native');validate_quest(q,nq)
            # Migration metadata must never be regenerated by an update.
            for field in ('legacyCounterKeys','legacyDefinitionHash'):
                if q.get(field)!=(old or {}).get(field):raise ValueError('既存カウンタの移行情報は変更できません')
            data['quest-catalog.json']['quests'][key]=q
            if nq:data['recurring-quests.json'][key]=nq
            else:data['recurring-quests.json'].pop(key,None)
        elif kind=='friendly':
            if id>=1500:raise ValueError('味方艦IDが不正です')
            row=after['growth']
            old=next((r for r in data['ship-growth.json'] if r[0]==id),None)
            if old!=p['before']:raise ValueError('艦IDと比較元が一致しません。planを再生成してください')
            if row[0] is None:row[0]=id
            if len(row)!=7 or row[0]!=id:raise ValueError('艦IDと能力成長の形式が不一致です')
            for x in row:n(x)
            for i in (1,4):
                a,b,c=row[i:i+3]
                if [a,b,c]!=[0,9999,9999] and not 0<=a<=b<=c<9999:raise ValueError('能力値が未確定または矛盾しています')
            data['ship-growth.json']=[r for r in data['ship-growth.json'] if r[0]!=id]+[row]
            data['ship-growth.json'].sort(key=lambda r:r[0])
        elif kind=='enemy':
            if id<1500:raise ValueError('敵艦IDが不正です')
            old=dict(hp=data['enemy-ship-hp.json']['hp'].get(key),slots=data['enemy-aircraft-slots.json'].get(key))
            if old!=p['before']:raise ValueError('敵艦IDと比較元が一致しません')
            if after.get('hp') is not None:data['enemy-ship-hp.json']['hp'][key]=n(after['hp'],1)
            if after.get('slots') is not None:
                if len(after['slots'])!=5:raise ValueError('搭載数はスロット別5要素を指定してください')
                for x in after['slots']:n(x,0,10000)
                data['enemy-aircraft-slots.json'][key]=after['slots']
        else:raise ValueError('未対応のデータ群です')
        url(p['evidence']['url'])
        if not re.fullmatch(r'[a-f0-9]{64}',p['evidence']['sha256']):raise ValueError('取得元ハッシュが不正です')
        applied.append(dict(kind=kind,id=id,source=p['evidence'],appliedAt=stamp()))
    return data,applied


def restore(work,root):
    journal=work/'journal.json'
    if not journal.exists():raise ValueError('復旧対象はありません')
    saved=load(journal)
    for name,item in saved['files'].items():
        if name not in FILES+['master-update-provenance.json']:raise ValueError('復旧対象が不正です')
        target=root/('definitions' if name=='master-update-provenance.json' else 'data')/name
        current=digest(target.read_bytes()) if target.exists() else None
        if current not in (item['before'],item['after']):raise ValueError('復旧対象に別の編集があります。自動上書きしません')
        if item['before'] is not None and digest((work/'backup'/name).read_bytes())!=item['before']:raise ValueError('バックアップの整合性が不正です')
    for name,item in saved['files'].items():
        target=root/('definitions' if name=='master-update-provenance.json' else 'data')/name
        backup=work/'backup'/name
        if item['before'] is None:target.unlink(missing_ok=True)
        else:
            raw=backup.read_bytes()
            if digest(raw)!=item['before']:raise ValueError('バックアップの整合性が不正です')
            atomic(target,raw)
    journal.unlink();print('変更前のマスターへ復旧しました')


@contextmanager
def update_lock(root):
    lock=root/'local/master-update.lock';lock.parent.mkdir(parents=True,exist_ok=True)
    with lock.open('a+b') as stream:
        stream.seek(0);stream.write(b'0');stream.flush();stream.seek(0)
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:yield
        finally:
            if os.name=='nt':stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(stream.fileno(),fcntl.LOCK_UN)


def apply(plan_path,work,root):
    with update_lock(root):_apply(plan_path,work,root)


def _apply(plan_path,work,root):
    if (work/'journal.json').exists():raise ValueError('前回の処理が中断されています。recoverを実行してください')
    data,applied=prepare(load(plan_path),root)
    if not applied:print('承認済み候補がありません。データは変更していません。');return
    changes={name:encoded(value) for name,value in data.items() if value!=load(root/'data'/name)}
    provenance_path=root/'definitions/master-update-provenance.json'
    provenance=load(provenance_path) if provenance_path.exists() else dict(schema=1,records=[])
    provenance['records'].extend(applied);changes['master-update-provenance.json']=encoded(provenance)
    journal=dict(files={})
    for name,raw in changes.items():
        target=root/('definitions' if name=='master-update-provenance.json' else 'data')/name
        before=target.read_bytes() if target.exists() else None
        if before is not None:atomic(work/'backup'/name,before)
        journal['files'][name]=dict(before=digest(before) if before is not None else None,after=digest(raw))
    atomic(work/'journal.json',encoded(journal))
    try:
        for name,raw in changes.items():atomic(root/('definitions' if name=='master-update-provenance.json' else 'data')/name,raw)
    except Exception:
        restore(work,root);raise
    atomic(work/'applied.json',encoded(dict(at=stamp(),records=applied,files=list(changes))))
    shutil.copyfile(work/'journal.json',work/'completed-journal.json');(work/'journal.json').unlink()
    print('反映:',len(applied),'件。manifest・Release・Gitは変更していません。回帰テスト後に配信版を作成してください。')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=ROOT/'definitions/master-update-sources.json')
    parser.add_argument('--work-dir',type=Path,default=ROOT/'local/master-update')
    parser.add_argument('--repo',type=Path,default=ROOT,help=argparse.SUPPRESS)
    sub=parser.add_subparsers(dest='command',required=True)
    f=sub.add_parser('fetch');f.add_argument('--refresh',action='store_true')
    i=sub.add_parser('import-page');i.add_argument('--key',required=True);i.add_argument('--file',type=Path,required=True)
    sub.add_parser('plan')
    d=sub.add_parser('discover-ships');d.add_argument('--master',type=Path,required=True);d.add_argument('--all',action='store_true');d.add_argument('--limit',type=int,default=20)
    a=sub.add_parser('apply');a.add_argument('--plan',type=Path)
    sub.add_parser('recover')
    args=parser.parse_args();work=args.work_dir.resolve();root=args.repo.resolve()
    if work==root or work.is_relative_to(root) and not work.is_relative_to(root/'local'):
        parser.error('作業フォルダにはlocal配下またはリポジトリ外を指定してください')
    work.mkdir(parents=True,exist_ok=True)
    try:
        if args.command in ('fetch','import-page'):
            cfg=config(args.config)
            if args.command=='import-page' and args.key not in {s['key'] for s in cfg['sources']}:raise ValueError('未登録の取得先キーです')
            failed=fetch(cfg,work,getattr(args,'refresh',False),(args.key,args.file) if args.command=='import-page' else None)
            if failed:return 2
        elif args.command=='plan':plan(config(args.config),work,root)
        elif args.command=='discover-ships':
            if not 1<=args.limit<=60:raise ValueError('limitは1～60です')
            discover_ships(config(args.config),work,args.master,root,args.all,args.limit)
        elif args.command=='apply':apply(args.plan or work/'review.json',work,root)
        else:
            with update_lock(root):restore(work,root)
    except (ValueError,KeyError,TypeError,OSError) as exc:
        print('中止:',str(exc),file=sys.stderr);return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
