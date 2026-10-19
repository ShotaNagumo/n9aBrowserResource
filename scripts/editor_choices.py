"""Name/ID options for the PC editor. Public master cache is local, never packaged."""
import json
import re
from urllib.request import Request, build_opener, HTTPRedirectHandler

import update_masters as masters

SOURCE = 'https://raw.githubusercontent.com/kcwiki/kancolle-data/master/api/api_start2.json'
GROUPS = ('ships', 'classes', 'types', 'hulls', 'nationalities', 'equipment', 'categories', 'cards', 'icons', 'missions', 'maps')
TYPES = {1:'海防艦',2:'駆逐艦',3:'軽巡洋艦',4:'重雷装巡洋艦',5:'重巡洋艦',6:'航空巡洋艦',7:'軽空母',8:'巡洋戦艦',9:'戦艦',10:'航空戦艦',11:'正規空母',12:'超弩級戦艦',13:'潜水艦',14:'潜水空母',15:'補給艦',16:'水上機母艦',17:'揚陸艦',18:'装甲空母',19:'工作艦',20:'潜水母艦',21:'練習巡洋艦',22:'補給艦',99:'任意の艦種'}
NATIONS = {1:'日本',2:'ドイツ',3:'イタリア',4:'アメリカ',5:'イギリス',6:'フランス',7:'ソ連・ロシア',8:'タイ',9:'ノルウェー',10:'スウェーデン',11:'オランダ',12:'オーストラリア'}


def human(value):
    return re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', value).replace('_', ' ')


def pairs(rows):
    result = {}
    for row in rows:
        ident = masters.n(row['api_id'], 1)
        name = row.get('api_name')
        if isinstance(name, str) and name.strip():
            if len(name) > 1000: raise ValueError('名称が長すぎます')
            result[str(ident)] = name.strip()
    return result


def normalize(value):
    if isinstance(value, dict) and 'api_data' in value: value = value['api_data']
    if not isinstance(value, dict) or not isinstance(value.get('api_mst_ship'), list): raise ValueError('公開ゲームマスターの形式が不正です')
    if not 1 <= len(value['api_mst_ship']) <= 20000: raise ValueError('艦データ件数が不正です')
    result = {k:{} for k in GROUPS}
    result['ships'] = pairs(value['api_mst_ship'])
    if not result['ships']: raise ValueError('艦名が含まれていません')
    for group, key in [('types','api_mst_stype'),('equipment','api_mst_slotitem'),('categories','api_mst_slotitem_equiptype'),('missions','api_mst_mission'),('maps','api_mst_mapinfo')]:
        rows = value.get(key, [])
        if not isinstance(rows, list) or len(rows) > 20000: raise ValueError('名称一覧の形式が不正です')
        result[group] = pairs(rows)
    members = {}
    for ship in value['api_mst_ship']:
        name = result['ships'].get(str(ship['api_id']))
        if not name: continue
        ident = ship.get('api_ctype')
        if type(ident) is int and ident > 0: members.setdefault(str(ident), []).append(name)
        sort = ship.get('api_sort_id')
        if type(sort) is int and sort > 0:
            key = str(sort//10)
            if key not in result['hulls']: result['hulls'][key] = name
    # These are representative members, not guessed canonical class names.
    result['classes'] = {k:' / '.join(list(dict.fromkeys(names))[:3]) for k,names in members.items()}
    for item in value.get('api_mst_slotitem', []):
        types = item.get('api_type', [])
        if isinstance(types, list) and len(types) > 3 and isinstance(item.get('api_name'), str):
            for group, index in [('cards',1),('icons',3)]:
                ident = types[index]
                if type(ident) is int and ident > 0 and str(ident) not in result[group]: result[group][str(ident)] = item['api_name']
    return result


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args): raise ValueError('名称取得先のリダイレクトには対応していません')


def refresh(root):
    req = Request(SOURCE, headers={'User-Agent':'n9aBrowserMasterEditor/1.0'})
    with build_opener(NoRedirect()).open(req, timeout=30) as response:
        raw = response.read(8*1024*1024+1)
    if len(raw) > 8*1024*1024: raise ValueError('公開マスターがサイズ上限を超えています')
    value = dict(schema=1, source=SOURCE, fetchedAt=masters.stamp(), sha256=masters.digest(raw), choices=normalize(json.loads(raw)))
    # Only names and public numeric identifiers survive, never the original response.
    masters.atomic(root/'local/manual-editor/choices.json', masters.encoded(value))
    return value


def load(root):
    result = {k:{} for k in GROUPS}
    result['types'] = {str(k):v for k,v in TYPES.items()}
    result['nationalities'] = {str(k):v for k,v in NATIONS.items()}
    path = root/'data/combat-reference.json'
    enums = masters.load(path).get('enums', {}) if path.exists() else {}
    for group, key in [('ships','ShipId'),('classes','ShipClass'),('equipment','EquipmentId'),('categories','EquipmentType')]:
        result[group].update({str(ident):human(name) for name,ident in enums.get(key, {}).items() if type(ident) is int and ident > 0})
    cache = root/'local/manual-editor/choices.json'
    status = dict(cached=False, source=None, fetchedAt=None)
    members = {}
    if cache.exists():
        try:
            data = masters.load(cache)
            if data['schema'] != 1: raise ValueError('未対応の名称形式です')
            for group in GROUPS:
                values = data['choices'].get(group, {})
                if not isinstance(values, dict) or len(values) > 20000: raise ValueError('名称キャッシュが不正です')
                for ident,name in values.items():
                    if not str(ident).isdigit() or not isinstance(name,str) or len(name)>4000: raise ValueError('名称キャッシュが不正です')
                if group == 'classes': members = values
                else: result[group].update(values)
            status.update(cached=True,source=data['source'],fetchedAt=data['fetchedAt'])
        except (ValueError, KeyError, TypeError, OSError):
            status['warning'] = '名称キャッシュを読めません。再取得してください。'
    # Matching explicit enum identifiers gives a canonical class name; unrelated
    # or similarly spelled ship names must never determine a class ID.
    for symbol, ident in enums.get('ShipClass', {}).items():
        if type(ident) is not int or ident <= 0: continue
        ship_id = enums.get('ShipId', {}).get(symbol)
        name = result['ships'].get(str(ship_id))
        if status['cached'] and name and str(ship_id) in data['choices'].get('ships', {}): result['classes'][str(ident)] = name+'型'
    for ident, names in members.items():
        if ident in result['classes']:
            if names not in result['classes'][ident]: result['classes'][ident] += ' — '+names
        else: result['classes'][ident] = '艦型 '+ident+' — '+names
    result['missions']['0'] = '任意の遠征'
    # Class selectors accept 0 as "do not limit class" when naming a ship.
    result['classes']['0'] = '艦型を限定しない'
    return dict(groups=result, status=status)
