"""Publish this resource repository and its prepared immutable Release. Never prints tokens.

Usage: python scripts/publish.py --publish
Uses GH_TOKEN/GITHUB_TOKEN or the existing git credential helper. No token file is created.
"""
import json,os,subprocess,sys,urllib.request,urllib.error
from pathlib import Path
from check_public_paths import check_repo
repo=Path(__file__).resolve().parents[1]
check_repo(repo)
if sys.argv[1:]!=['--publish']:raise SystemExit('Usage: python scripts/publish.py --publish')
token=os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
if not token:
    result=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',text=True,capture_output=True)
    values=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
    token=values.get('password')
if not token:raise SystemExit('GitHub authentication is required; no changes published.')
headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','User-Agent':'n9aBrowserResource-publisher'}
base='https://api.github.com'
def api(path,method='GET',value=None):
    data=json.dumps(value).encode() if value is not None else None
    request=urllib.request.Request(base+path,data=data,method=method,headers=headers|({'Content-Type':'application/json'} if data else {}))
    try:
        with urllib.request.urlopen(request,timeout=60) as response:return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code==404:return None
        raise SystemExit(f'GitHub operation failed: HTTP {error.code}; credentials were not printed.')
user=api('/user')
if user['login'].lower()!='shotanagumo':raise SystemExit('Authenticate as ShotaNagumo before publishing.')
target='/repos/ShotaNagumo/n9aBrowserResource'
remote=api(target)
created=remote is None
if remote is None:
    remote=api('/user/repos','POST',dict(name='n9aBrowserResource',description='Public data, icons and palette for n9aBrowser',private=False,auto_init=False))
if remote.get('private'):raise SystemExit('Existing repository is private; visibility was not changed.')
origin=subprocess.run(['git','-C',str(repo),'remote','get-url','origin'],text=True,capture_output=True)
if origin.returncode:
    subprocess.run(['git','-C',str(repo),'remote','add','origin','https://github.com/ShotaNagumo/n9aBrowserResource.git'],check=True)
elif origin.stdout.strip()!='https://github.com/ShotaNagumo/n9aBrowserResource.git':raise SystemExit('Unexpected origin; publication stopped.')
manifest=json.loads((repo/'manifest.json').read_text(encoding='utf-8'))
tag='resources-'+manifest['revision']
# Push a publication branch first so GitHub can attach a Release to this commit.
# The app's develop/manifest.json endpoint is advanced only after all assets are public.
subprocess.run(['git','-C',str(repo),'push','origin','HEAD:refs/heads/codex/resource-publication'],check=True)
commit=subprocess.run(['git','-C',str(repo),'rev-parse','HEAD'],check=True,capture_output=True,text=True).stdout.strip()
release=api(target+'/releases/tags/'+tag)
if release is None:
    release=api(target+'/releases','POST',dict(tag_name=tag,target_commitish=commit,name=tag,body='公開マスター・採用アイコン・配色。manifestの形式版と対応アプリ版を確認してください。',draft=True,prerelease=False))
if not release['draft']:raise SystemExit('Release already published; no assets overwritten.')
existing={v['name']:v for v in api(target+f'/releases/{release["id"]}/assets')}
for spec in manifest['packages']:
    if '/releases/download/'+tag+'/' not in spec['url']:continue # Reuse immutable packages from an earlier Release.
    name=spec['name']+'.zip'
    if name in existing:raise SystemExit('Release asset already exists; inspect the draft before retrying.')
    data=(repo/'dist'/tag/name).read_bytes()
    import hashlib
    if len(data)!=spec['size'] or hashlib.sha256(data).hexdigest()!=spec['sha256']:raise SystemExit('Package differs from manifest; publication stopped.')
    url=release['upload_url'].split('{',1)[0]+'?name='+name
    request=urllib.request.Request(url,data=data,method='POST',headers=headers|{'Content-Type':'application/zip'})
    with urllib.request.urlopen(request,timeout=180) as response:json.load(response)
api(target+f'/releases/{release["id"]}','PATCH',dict(draft=False))
subprocess.run(['git','-C',str(repo),'push','-u','origin','HEAD:refs/heads/develop'],check=True)
if created:api(target,'PATCH',dict(default_branch='develop'))
print('Published https://github.com/ShotaNagumo/n9aBrowserResource and Release '+tag)
