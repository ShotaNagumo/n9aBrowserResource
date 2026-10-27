from pathlib import Path
import json,hashlib,zipfile,sys

from check_public_paths import check_repo
repo=Path(__file__).resolve().parents[1]
check_repo(repo)
# Adopted runtime icons must not silently vanish after a merge.
for icon in ('dashboard/FleetUpdateStopped.png', 'battle/MvpCrown-white.png'):
 if not (repo/'icons'/icon).is_file():raise SystemExit('Required runtime icon is missing: '+icon)
previous=json.loads((repo/'manifest.json').read_text(encoding='utf-8')) if (repo/'manifest.json').exists() else {}
revision=sys.argv[1] if len(sys.argv)>1 else '2026.10.18.1'
tag='resources-'+revision
output=repo/'dist'/tag
output.mkdir(parents=True,exist_ok=True)
def sha(data): return hashlib.sha256(data).hexdigest()
groups={'master':{},'icons':{},'palette':{'palette.json':repo/'palette.json'}}
for f in (repo/'data').glob('*.json'):groups['master']['data/'+f.name]=f
for folder in ['equipment','proficiency','userinfo','dashboard','battle']:
 for f in (repo/'icons'/folder).glob('*.png'):
  groups['icons']['assets/'+('userinfo_material' if folder=='userinfo' else folder)+'/'+f.name]=f
catalog=json.loads((repo/'data/quest-catalog.json').read_text(encoding='utf-8'))
# conditionsText/counterPeriod require the next reader after versionCode 194.
minimum=195 if any('conditionsText' in q or 'counterPeriod' in q for q in catalog['quests'].values()) else 193
manifest=dict(schema=1,revision=revision,minAppVersion=max(minimum,previous.get('minAppVersion',193)),packages=[])
for name,files in groups.items():
 path=output/(name+'.zip')
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for target,source in sorted(files.items()):
   info=zipfile.ZipInfo(target,date_time=(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
   z.writestr(info,source.read_bytes())
 spec=dict(name=name,url=f'https://github.com/ShotaNagumo/n9aBrowserResource/releases/download/{tag}/{name}.zip',size=path.stat().st_size,sha256=sha(path.read_bytes()),files={})
 for target,source in sorted(files.items()):
  data=source.read_bytes();spec['files'][target]=dict(size=len(data),sha256=sha(data))
 for old in previous.get('packages',[]):
  if old['name']==name and old['sha256']==spec['sha256'] and old['files']==spec['files']:spec['url']=old['url']
 manifest['packages'].append(spec)
(repo/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
# Offline directory for the application's regression tests, not used by Android builds.
fixture=repo/'test-runtime'
fixture.mkdir(exist_ok=True)
for name in groups:
 with zipfile.ZipFile(output/(name+'.zip')) as z:z.extractall(fixture)
(fixture/'manifest.json').write_text((repo/'manifest.json').read_text(encoding='utf-8'),encoding='utf-8')
print('Validated JSON files:',len(list((repo/'data').glob('*.json')))+1)
for f in (repo/'data').glob('*.json'):json.loads(f.read_text(encoding='utf-8'))
json.loads((repo/'palette.json').read_text(encoding='utf-8'))
print('Release:',tag,'/ packages:',', '.join(groups),' / images:',len(groups['icons']))
