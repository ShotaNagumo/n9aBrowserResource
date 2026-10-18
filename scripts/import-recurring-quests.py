"""Regenerate the reviewed, offline Kotlin table from the pinned Sniffer source.
No network access; inspect the generated diff before updating the application.
"""
import pathlib, re, json, sys

root = pathlib.Path(__file__).resolve().parent.parent
source = pathlib.Path(sys.argv[1]) / 'KancolleSniffer/Model/QuestCountList.cs'
text = source.read_text(encoding='utf-8-sig')
types = dict(DE=1, DD=2, CL=3, CLT=4, CT=21, CA=5, CAV=6, CVL=7, CV=11, CVB=18, SS=13, SSV=14, AP=15)
rows = []
records = {}
excluded = []
for m in re.finditer(r'// ([^\n]+)\n\s*\{(\d+), new (\w+) \{([^\n]+)\}\}', text):
    name, id, kind, fields = m.groups()
    # Seasonal IDs are reused with different conditions; never freeze those into a permanent table.
    if any(s in name for s in ['限定', '周年', '節分', '桃の節句', '梅雨', '秋祭り', '南瓜', '新春', '春です！']) or 'Disabled = true' in fields:
        excluded.append(id); continue
    def val(key, default=None):
        x = re.search(r'\b'+key+r' = (\[.*?\](?:\])?|"[^"]*"|\w+)(?=, \w+ =|$)', fields)
        return x[1] if x else default
    def nums(key):
        v = val(key, '[]')
        return [types[x] if x in types else int(x) for x in re.findall(r'\w+', v)]
    interval = val('Interval')
    period = {'Daily':1,'Weekly':2,'Monthly':3,'Quarterly':5}.get(interval, 100+int(interval[6:]) if interval.startswith('Yearly') else 0)
    maxs = nums('MaxArray') or [int(val('Max','0'))]
    rank = val('Rank','"E"').strip('"')
    ranks = re.findall(r'"(\w+)"', val('Ranks',''))
    tasks = []
    def task(event, target, ids=[], rank='E', aux=[], required=0):
        tasks.append(f'RecurringTask("{event}", {target}, listOf({", ".join(map(str,ids))}), "{rank}", listOf({", ".join(map(str,aux))}), {required})')
    if kind == 'QuestSortie':
        maps=nums('Maps')
        if len(maxs)>1:
            for i,n in enumerate(maxs): task('battle',n,[maps[i]],ranks[i] if ranks else rank)
        else: task('battle',maxs[0],maps,rank)
    elif kind == 'QuestPractice': task('practice',maxs[0],rank=rank)
    elif kind == 'QuestEnemyType': task('sink',maxs[0],nums('EnemyType'))
    elif kind == 'QuestMission':
        ids=nums('Ids')
        if len(maxs)>1:
            for i,n in enumerate(maxs): task('mission',n,[ids[i]])
        else: task('mission',maxs[0],ids)
    elif kind == 'QuestDestroyItem':
        groups = [[int(x) for x in re.findall(r'\d+', g)] for g in re.findall(r'\[([^\[\]]+)\]', val('Types',''))]
        selectors = [('discardType',g) for g in groups] + [('discardId',[x]) for x in nums('Ids')]
        if len(maxs)>1:
            assert len(selectors)==len(maxs),(id,fields,selectors)
            for (e,s),n in zip(selectors,maxs): task(e,n,s)
        else:
            assert len(selectors)==1,(id,selectors)
            task(selectors[0][0],maxs[0],selectors[0][1])
    elif kind == 'QuestPowerUp': task('modernize',maxs[0],nums('Types'),aux=nums('ItemsTypes'),required=int(val('Requires','0')))
    elif id == '214':
        for e,n in zip(['sortie','sVictory','boss','bossVictory'],maxs): task(e,n)
    else:
        event = {'503':'repair','504':'supply','605':'develop','607':'develop','606':'build','608':'build','609':'scrapShip','619':'improve','1166':'improve','1167':'improve','613':'discardOperation'}[id]
        task(event,maxs[0])
    rows.append(f'        {id} to RecurringQuest({period}, "{name}", listOf(\n            '+',\n            '.join(tasks)+'))')
for row in rows:
    m = re.search(r'(\d+) to RecurringQuest\((\d+), "([^"]+)", listOf\((.*)\)\)', row, re.S)
    tasks_json=[]
    for t in re.finditer(r'RecurringTask\("([^"]+)", (\d+), listOf\(([^)]*)\), "([^"]+)", listOf\(([^)]*)\), (\d+)\)',m[4]):
        nums=lambda v:[int(x) for x in v.split(',') if x.strip()]
        tasks_json.append(dict(event=t[1],target=int(t[2]),ids=nums(t[3]),rank=t[4],materialTypes=nums(t[5]),required=int(t[6])))
    assert tasks_json
    records[m[1]]=dict(period=int(m[2]),name=m[3],tasks=tasks_json)
(root/'data/recurring-quests.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'{len(records)} recurring quests generated')
