"""Convert the pinned enemy HP record to the public, optional preview fallback table."""
from pathlib import Path
import csv, hashlib, io, json, sys
repo=Path(__file__).resolve().parents[1]
raw=Path(sys.argv[1]).read_bytes()
revision=sys.argv[2]
assert len(revision)==40 and all(c in '0123456789abcdef' for c in revision)
rows=csv.DictReader(io.StringIO(raw.decode('cp932')))
hp={}
for row in rows:
    ship=int(row['艦船ID'])
    if ship<1500: continue
    first=int(row['耐久初期']); maximum=int(row['耐久最大'])
    # Zero is an unknown sentinel, not a sunk enemy. Never guess variable HP.
    if first<=0 or first!=maximum: continue
    assert ship not in hp and first<=100000
    hp[ship]=first
assert hp
value=dict(schema=1,source=dict(repository='ElectronicObserverEN/ElectronicObserver',revision=revision,path='ElectronicObserver.Avalonia/Assets/Record/ShipParameterRecord.csv',sha256=hashlib.sha256(raw).hexdigest()),hp={str(k):v for k,v in sorted(hp.items())})
(repo/'data/enemy-ship-hp.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Enemy HP records:',len(hp))
