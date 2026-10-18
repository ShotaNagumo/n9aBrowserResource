"""Extract MIT-licensed numeric rules from the pinned ElectronicObserverEN checkout.

Usage: python scripts/import_combat_reference.py .tools/research-74en
No game/account data is read. Unrecognized initializer syntax fails closed.
"""
import json
import re
import sys
import subprocess
from pathlib import Path
import xml.etree.ElementTree as ET

source = Path(sys.argv[1])
revision='5b74e9ac449e892c3b64dae43fd2d75c98f544fb'
actual=subprocess.run(['git','-C',str(source),'rev-parse','HEAD'],check=True,capture_output=True,text=True).stdout.strip()
if actual!=revision:
    raise SystemExit(f'Review and update the pinned revision before importing: {actual}')
types = source / 'ElectronicObserver.Core/Types'
def read(path):
    return path.read_text(encoding='utf-8-sig')
def enum(name):
    return {k: int(v) for k,v in re.findall(r'^\s*(\w+)\s*=\s*(\d+)',read(types / (name+'.cs')),re.M)}
enums = {n: enum(n) for n in ('ShipId','ShipClass','EquipmentId','EquipmentType')}
def clean(text):
    return re.sub(r'/\*.*?\*/|//[^\n]*','',text,flags=re.S)
def objects(text):
    depth=0; start=None
    for i,c in enumerate(text):
        if c=='{':
            if depth==0: start=i+1
            depth+=1
        elif c=='}':
            depth-=1
            if depth==0: yield text[start:i]
    assert depth==0
def values(text):
    result={}
    for key,value in re.findall(r'(\w+)\s*=\s*(\[[^\]]*\]|[^,\n]+)',text):
        value=value.strip()
        if value.startswith('['):
            result[key]=[enums[typ][name] for typ,name in re.findall(r'(ShipId|ShipClass)\.(\w+)',value)]
        else: result[key]=None if value=='null' else float(value) if '.' in value else int(value)
    return result

text=clean(read(types/'AntiAir/AntiAirCutIn.cs'))
priorities=list(map(int,re.search(r'ActivationPriorities.*?\[(.*?)\]',text,re.S)[1].replace('\n','').replace('\t','').strip().strip(',').split(',')))
body=text.split('private static List<AntiAirCutIn> CutIns',1)[1].split('public static IEnumerable',1)[0]
body=body.split('=',1)[1]
cutins=[]
for obj in objects(body):
    head,conditions=obj.split('Conditions =',1)
    row=values(head)
    row['conditions']=[values(c) for c in objects(conditions)]
    row['priority']=priorities.index(row['Id']) if row['Id'] else 9999
    cutins.append(row)
assert len(cutins)==53 and {c['Id'] for c in cutins}==set(range(53))

extensions=read(types/'Extensions/ShipDataExtensions.cs')+'\n'+read(types/'Extensions/EquipmentDataExtensions.cs')
equipment_sets={}
for method,body in re.findall(r'(?:public|private) static (?:bool|int) (\w+)\([^;{]*?=>\s*(.*?);',extensions,re.S):
    ids=re.findall(r'EquipmentId\.(\w+)',body)
    if ids: equipment_sets[method]=list(dict.fromkeys(enums['EquipmentId'][i] for i in ids))
texts={}
for file in (types/'Attacks/AttackResources.resx',types.parent/'Properties/DayAirAttackCutinKindResources.resx',
             source/'ElectronicObserver/Window/GeneralRes.resx',source/'ElectronicObserver/Window/Wpf/Fleet/FormFleet.resx'):
    if file.exists():
        texts.update({e.attrib['name']:e.findtext('value') for e in ET.fromstring(read(file)).findall('data')})
result=dict(revision=revision,enums=enums,equipmentSets=equipment_sets,cutins=cutins,texts=texts)
out=Path(__file__).resolve().parents[1]/'data/combat-reference.json'
out.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
print(f'{len(cutins)} AACI rules, {len(equipment_sets)} equipment predicates -> {out}')

# Minimal public master records for independent upstream golden-value regression tests.
test_text='\n'.join(read(source/'ElectronicObserverCoreTests'/name) for name in ('DayAttackTests.cs','NightAttackTests.cs','AntiAirCutInTests.cs'))
test_text+='\n'+'\n'.join(read(p) for p in sorted((source/'ElectronicObserverCoreTests/SpecialAttacks').glob('*.cs')))
fixture={}
for key,filename,enum_name,id_field in (('ships','ships.json','ShipId','ShipId'),('equipment','equipment.json','EquipmentId','EquipmentId')):
    names=re.findall(enum_name+r'\.(\w+)',test_text)
    ids={enums[enum_name][name] for name in names}
    records=json.loads(read(source/'ElectronicObserver.TestData/Generated'/filename))
    fixture[key]=[{k:v for k,v in record.items() if isinstance(v,int)} for record in records if record[id_field] in ids]
fixture_path=Path(__file__).resolve().parents[1]/'test-runtime/ship-combat-fixtures.json'
fixture_path.parent.mkdir(exist_ok=True)
fixture_path.parent.mkdir(parents=True,exist_ok=True)
fixture_path.write_text(json.dumps(fixture,separators=(',',':'))+'\n',encoding='utf-8')
