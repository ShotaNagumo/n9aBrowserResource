"""Convert a pinned EO Data snapshot into named, declarative n9aBrowser quest data.

Usage: python scripts/import_quest_catalog.py SOURCE_DIRECTORY COMMIT_SHA
SOURCE_DIRECTORY contains descriptions.json, trackers.json, metadata.json.
No network, account data, or executable expressions are included in the output.
"""
import json,sys,re,hashlib
from pathlib import Path
repo=Path(__file__).resolve().parents[1]
source=Path(sys.argv[1]); revision=sys.argv[2]
assert re.fullmatch('[0-9a-f]{40}',revision)
def read(name):return json.loads((source/name).read_text(encoding='utf-8-sig'))
def compact(v):return json.dumps(v,ensure_ascii=False,separators=(',',':'))
def optional(v):return re.sub(r'<br\s*/?>','\n',v,flags=re.I) if isinstance(v,str) and v.strip() else None
def all_(*c):return {'op':'all','conditions':list(c)}
def count(selector,min=0,max=None,positions=None):
    d={'op':'count','selector':selector,'min':min}
    if max is not None:d['max']=max
    if positions is not None:d['positions']=positions
    return d
def compare(selector,target,mode,positions=None):
    return count(selector,0 if mode==2 else target,target if mode in [1,2] else None,positions)
def ship(d):
    return {'op':'ship','id':d[0],'remodel':['family','atLeast','exact'][d[2]],'class':d[3] if len(d)>3 and d[3] is not None else 0}
def group(g):return {'op':['all','any'][g[0]],'conditions':[condition(c) for c in g[1]]}
def condition(c):
    kind,d=c
    if kind==0:return group(d)
    if kind in [1,7]:return count(ship(d),1,positions=[1] if d[1] else None)
    if kind in [3,8]:return {'op':'candidates','min':d[1],'candidates':[{'selector':ship(v),'positions':[1] if v[1] else list(range(1,8)),'countAll':v[0]==0 and len(v)>3 and v[3]!=0} for v in d[0]]}
    if kind in [2,6]:
        selector={'op':'type' if kind==2 else 'nationality','values':d[0]}
        selected=selector
        if kind==2 and len(d)>4 and d[4]:selected=all_(selector,{'op':'level','min':d[4]})
        result=compare(selected,d[1],d[3] if len(d)>3 and d[3] is not None else 0)
        return all_(result,count(selector,1,positions=[1])) if d[2] else result
    if kind==4:return count({'op':'not','condition':{'op':'type','values':d[0]}},0,0)
    if kind==5:return count({'op':'ship','id':d[0],'remodel':['family','atLeast','exact'][d[2]]},1,positions=[d[1]])
    return {'op':'unsupported','sourceType':kind}
ranks=['any','battle','D','C','B','A','S','SS']
def task(t):
    k,d=t
    if k in [0,2]:
        q={'kind':'bossBattle' if k==0 else 'nodeBattle','map':dict(zip(['area','number'],d[0])),'rank':ranks[d[1]],'target':d[2]}
        if k==2:q['cells']=d[3]
        return q
    if k==1:return {'kind':'mission','missionIds':d[0],'target':d[1]}
    if k in [3,4,5,6]:return {'kind':'discard','selectBy':['id','category','cardType','icon'][k-3],'ids':[d[0]],'target':d[1]}
    if k==7:return {'kind':'reachNode','map':dict(zip(['area','number'],d[0])),'cells':d[2],'target':d[1]}
    if k==8:return {'kind':'firstClear','map':dict(zip(['area','number'],d[0])),'target':d[1]}
    if k==9:return {'kind':'practice','rank':ranks[d[0]],'target':d[1]}
    return {'kind':'unsupported','sourceType':k,'target':1}
overrides=json.loads((repo/'definitions/quest-overrides.json').read_text(encoding='utf-8'))
quests={}
for id,q in read('descriptions.json').items():
    if id=='version':continue
    quests[id]={'name':optional(q.get('name_jp')),'description':optional(q.get('desc_jp')),'explanation':optional(q.get('desc')),'tasks':[]}
for row in read('trackers.json'):
    id=str(row[0][0]); q=quests.setdefault(id,{'tasks':[]})
    q['tasks']=[task(t) for t in row[1]]
    old_group=compact(row[2]) if len(row)>2 and row[2] is not None and row[2][1] else None
    if old_group:q['formation']=group(row[2])
    q['legacyCounterKeys']=[compact(t)+'|'+(old_group or 'null')+'|false' for t in row[1]]
for item in read('metadata.json'):quests.setdefault(str(item['id']),{'tasks':[]})['period']=item['resetType']
for id,override in overrides['fallbacks'].items():
    q=quests.setdefault(id,{'tasks':[]})
    for key,value in override.items():
        if key in ['formation','tasks']:
            if not q.get(key):q[key]=value
        else:q.setdefault(key,value)
for q in quests.values():
    if q.get('legacyCounterKeys'):
        semantic={'tasks':q.get('tasks',[]),'formation':q.get('formation'),'fleetIds':q.get('fleetIds')}
        q['legacyDefinitionHash']=hashlib.sha256(json.dumps(semantic,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
result={'schema':1,'source':{'repository':'ElectronicObserverEN/Data','revision':revision,'files':{n:hashlib.sha256((source/n).read_bytes()).hexdigest() for n in ['descriptions.json','trackers.json','metadata.json']}},'quests':dict(sorted(quests.items(),key=lambda p:int(p[0]))),'fallbacks':overrides['fallbacks'],'mapAliases':overrides['mapAliases'],'arrivalMaps':overrides['arrivalMaps']}
(repo/'data/quest-catalog.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Normalized quests:',len(quests))
