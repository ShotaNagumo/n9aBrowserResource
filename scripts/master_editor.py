"""Local GUI for public master data. Python 3.10+, standard library only."""
import argparse
import copy
import difflib
import json
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import update_masters as masters
from check_public_paths import LOCAL_PATH

ROOT = Path(__file__).resolve().parents[1]
ASSETS = Path(__file__).resolve().parent / 'master_editor'


class Editor:
    def __init__(self, root):
        self.root = Path(root)
        self.work = self.root / 'local/manual-editor'
        self.previews = {}
        self.mutex = threading.RLock()

    def snapshot(self):
        base = masters.baseline(self.root)
        provenance = self.root/'definitions/master-update-provenance.json'
        base['provenance'] = masters.digest(provenance.read_bytes()) if provenance.exists() else None
        return masters.state(self.root), base, masters.digest(masters.encoded(base))

    def names(self):
        path = self.root / 'definitions/master-update-provenance.json'
        records = masters.load(path).get('records', []) if path.exists() else []
        return {(r['kind'], r['id']): r.get('name', '') for r in records if r.get('source', {}).get('kind') == 'manual'}

    def bootstrap(self):
        with self.mutex:
            data, _, revision = self.snapshot()
            names = self.names()
            quests = data['quest-catalog.json']['quests']
            native = data['recurring-quests.json']
            hp = data['enemy-ship-hp.json']['hp']
            slots = data['enemy-aircraft-slots.json']
            return dict(revision=revision, pending=(self.work/'journal.json').exists(),
                        lists=dict(quest=[dict(id=int(i), name=quests.get(i, {}).get('name') or native.get(i, {}).get('name', '名称未登録')) for i in sorted(set(quests) | set(native), key=int)],
                                   friendly=[dict(id=r[0], name=names.get(('friendly', r[0]), '')) for r in sorted(data['ship-growth.json']) if 0 < r[0] < 1500],
                                   enemy=[dict(id=i, name=names.get(('enemy', i), '')) for i in sorted({int(i) for i in hp} | {int(i) for i in slots})]))

    def record(self, kind, ident):
        with self.mutex:
            data, _, revision = self.snapshot()
            key = str(masters.n(ident, 1))
            if kind == 'quest':
                q = copy.deepcopy(data['quest-catalog.json']['quests'].get(key))
                native = data['recurring-quests.json'].get(key)
                if q is None and native is None: raise ValueError('任務が見つかりません')
                if q is None: q = dict(name=native['name'], period=native['period'], tasks=[])
                after = dict(quest=q, native=native)
            elif kind == 'friendly':
                row = next((r for r in data['ship-growth.json'] if r[0] == ident), None)
                if row is None: raise ValueError('艦データが見つかりません')
                after = dict(growth=row)
            elif kind == 'enemy':
                after = dict(hp=data['enemy-ship-hp.json']['hp'].get(key), slots=data['enemy-aircraft-slots.json'].get(key))
                if all(v is None for v in after.values()): raise ValueError('敵艦が見つかりません')
            else: raise ValueError('データ種別が不正です')
            return dict(id=ident, kind=kind, revision=revision, after=after, name=self.names().get((kind, ident), ''))

    def prepare(self, payload):
        if not isinstance(payload, dict): raise ValueError('入力全体はJSONオブジェクトで指定してください')
        data, base, revision = self.snapshot()
        if payload['revision'] != revision: raise ValueError('他の保存によりマスターが変わりました。一覧を再読み込みしてください')
        kind = payload['kind']; ident = masters.n(payload['id'], 1); key = str(ident)
        mode = payload['mode']; after = copy.deepcopy(payload['after'])
        if not isinstance(after, dict): raise ValueError('編集内容はJSONオブジェクトで指定してください')
        if mode not in ('new', 'edit'): raise ValueError('追加・編集の指定が不正です')
        if kind == 'quest':
            before = dict(quest=data['quest-catalog.json']['quests'].get(key), native=data['recurring-quests.json'].get(key))
            exists = before['quest'] is not None or before['native'] is not None
            q = after['quest']; native = after.get('native')
            if not isinstance(q, dict) or native is not None and not isinstance(native, dict): raise ValueError('任務条件の構造が不正です')
            if not isinstance(q.get('name'), str) or not q['name'].strip(): raise ValueError('任務名を入力してください')
            for field in ('legacyCounterKeys', 'legacyDefinitionHash'):
                if q.get(field) != (before['quest'] or {}).get(field): raise ValueError('旧カウンタの移行情報は変更できません')
            masters.validate_quest(q, native, allow_untracked=payload.get('tracking') == 'none')
            data['quest-catalog.json']['quests'][key] = q
            if native: data['recurring-quests.json'][key] = native
            else: data['recurring-quests.json'].pop(key, None)
            name = q['name']
        elif kind == 'friendly':
            if ident >= 1500: raise ValueError('味方艦の内部IDは1～1499です')
            before = next((r for r in data['ship-growth.json'] if r[0] == ident), None)
            exists = before is not None
            row = after['growth']
            if len(row) != 7 or row[0] != ident: raise ValueError('成長データは内部IDと6つの能力値で指定してください')
            for value in row: masters.n(value)
            for start in (1, 4):
                a, b, c = row[start:start+3]
                if [a, b, c] != [0, 9999, 9999] and not 0 <= a <= b <= c < 9999:
                    raise ValueError('初期下限≦初期上限≦Lv99値となるように入力してください')
            data['ship-growth.json'] = sorted([r for r in data['ship-growth.json'] if r[0] != ident] + [row])
            name = payload.get('name', '')
        elif kind == 'enemy':
            if ident < 1500: raise ValueError('敵艦の内部IDは1500以上です')
            before = dict(hp=data['enemy-ship-hp.json']['hp'].get(key), slots=data['enemy-aircraft-slots.json'].get(key))
            exists = any(v is not None for v in before.values())
            if after.get('hp') is None and after.get('slots') is None: raise ValueError('耐久または個別搭載数を入力してください')
            for field in ('hp', 'slots'):
                if before[field] is not None and after.get(field) is None: raise ValueError('既存の耐久・搭載数は空欄にして削除できません')
            if after.get('hp') is not None: data['enemy-ship-hp.json']['hp'][key] = masters.n(after['hp'], 1)
            if after.get('slots') is not None:
                if not isinstance(after['slots'], list) or len(after['slots']) != 5: raise ValueError('個別搭載数は5スロット分入力してください')
                for value in after['slots']: masters.n(value, 0, 10000)
                data['enemy-aircraft-slots.json'][key] = after['slots']
            name = payload.get('name', '')
        else: raise ValueError('データ種別が不正です')
        if mode == 'new' and exists: raise ValueError('この内部IDは登録済みです。一覧から選んで編集してください')
        if mode == 'edit' and (not exists or payload.get('originalId') != ident): raise ValueError('編集対象のIDを変更できません')
        note = payload.get('note', '')
        if not isinstance(name, str) or not isinstance(note, str): raise ValueError('名前・メモは文字列で指定してください')
        note = note.strip()
        if len(name) > 1000 or len(note) > 4000: raise ValueError('名前・メモが長すぎます')
        if LOCAL_PATH.search(json.dumps(dict(after=after, name=name, note=note), ensure_ascii=False)):
            raise ValueError('公開データに端末のファイルパスは保存できません')
        changes = {f: masters.encoded(value) for f, value in data.items() if value != masters.load(self.root/'data'/f)}
        memo_changed = kind != 'quest' and name != self.names().get((kind, ident), '')
        if not changes and not memo_changed and not note: raise ValueError('データに変更がありません')
        provenance_path = self.root/'definitions/master-update-provenance.json'
        provenance = masters.load(provenance_path) if provenance_path.exists() else dict(schema=1, records=[])
        provenance['records'].append(dict(kind=kind, id=ident, name=name, source=dict(kind='manual', note=note), appliedAt=masters.stamp()))
        changes['master-update-provenance.json'] = masters.encoded(provenance)
        return dict(base=base, changes=changes, before=before, after=after, name=name, id=ident)

    def preview(self, payload):
        with self.mutex:
            plan = self.prepare(payload)
            token = secrets.token_hex(24)
            if len(self.previews) >= 20: self.previews.pop(next(iter(self.previews)))
            self.previews[token] = plan
            diff = ''.join(difflib.unified_diff(masters.encoded(plan['before']).decode().splitlines(True),
                                               masters.encoded(plan['after']).decode().splitlines(True), fromfile='変更前', tofile='変更後'))
            return dict(token=token, id=plan['id'], name=plan['name'], files=list(plan['changes']), diff=diff)

    def save(self, token):
        with self.mutex, masters.update_lock(self.root):
            plan = self.previews.pop(token, None)
            if plan is None: raise ValueError('確認内容が期限切れです。変更を再確認してください')
            if plan['base'] != self.snapshot()[1]: raise ValueError('確認後にデータが変更されました。一覧を再読み込みしてください')
            if (self.work/'journal.json').exists() or (self.root/'local/master-update/journal.json').exists():
                raise ValueError('中断した更新があります。先に復旧してください')
            journal = dict(files={})
            for name, raw in plan['changes'].items():
                target = self.root/('definitions' if name == 'master-update-provenance.json' else 'data')/name
                previous = target.read_bytes() if target.exists() else None
                if previous is not None: masters.atomic(self.work/'backup'/name, previous)
                journal['files'][name] = dict(before=masters.digest(previous) if previous is not None else None, after=masters.digest(raw))
            masters.atomic(self.work/'journal.json', masters.encoded(journal))
            try:
                for name, raw in plan['changes'].items():
                    masters.atomic(self.root/('definitions' if name == 'master-update-provenance.json' else 'data')/name, raw)
            except Exception:
                masters.restore(self.work, self.root)
                raise
            masters.atomic(self.work/'completed-journal.json', masters.encoded(journal))
            (self.work/'journal.json').unlink()
            return dict(message='保存しました。公開・配信は通常のレビュー後に別途行ってください。')

    def recover(self):
        with self.mutex, masters.update_lock(self.root):
            masters.restore(self.work, self.root)
            self.previews.clear()
            return dict(message='中断した保存を復旧しました。')


def handler(editor, token, assets=ASSETS):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass

        def reply(self, code, body, kind='application/json; charset=utf-8'):
            if not isinstance(body, bytes): body = masters.encoded(body)
            self.send_response(code)
            for key, value in {'Content-Type': kind, 'Content-Length': str(len(body)), 'Cache-Control': 'no-store',
                               'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer',
                               'Content-Security-Policy': "default-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"}.items(): self.send_header(key, value)
            self.end_headers(); self.wfile.write(body)

        def allowed(self, api):
            hosts = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            if self.headers.get('Host') not in hosts: return False
            origin = self.headers.get('Origin')
            if origin and origin not in {'http://'+h for h in hosts}: return False
            return not api or secrets.compare_digest(self.headers.get('X-Editor-Token', ''), token)

        def do_GET(self):
            path = urlsplit(self.path)
            if not self.allowed(path.path.startswith('/api/')): self.reply(403, dict(error='この画面からのみ操作できます')); return
            try:
                if path.path == '/api/bootstrap': self.reply(200, editor.bootstrap())
                elif path.path == '/api/record':
                    query = parse_qs(path.query)
                    self.reply(200, editor.record(query['kind'][0], int(query['id'][0])))
                elif path.path in ('/', '/editor.js', '/editor.css'):
                    file, kind = {'/': ('index.html', 'text/html'), '/editor.js': ('editor.js', 'text/javascript'), '/editor.css': ('editor.css', 'text/css')}[path.path]
                    raw = (assets/file).read_bytes()
                    if file == 'index.html': raw = raw.replace(b'__EDITOR_TOKEN__', token.encode())
                    self.reply(200, raw, kind+'; charset=utf-8')
                else: self.reply(404, dict(error='見つかりません'))
            except (ValueError, KeyError, TypeError, OSError) as exc: self.reply(400, dict(error=str(exc)))

        def do_POST(self):
            if not self.allowed(True): self.reply(403, dict(error='この画面からのみ操作できます')); return
            try:
                size = int(self.headers.get('Content-Length', '-1'))
                if not 0 <= size <= 1024*1024: self.reply(413, dict(error='入力が大きすぎます')); return
                if self.headers.get('Content-Type') != 'application/json': self.reply(415, dict(error='JSONのみ受け付けます')); return
                value = json.loads(self.rfile.read(size))
                route = urlsplit(self.path).path
                if route == '/api/preview': result = editor.preview(value)
                elif route == '/api/save': result = editor.save(value['token'])
                elif route == '/api/recover': result = editor.recover()
                else: self.reply(404, dict(error='見つかりません')); return
                self.reply(200, result)
            except (ValueError, KeyError, TypeError, OSError) as exc: self.reply(400, dict(error=str(exc)))
    return Handler


def main():
    parser = argparse.ArgumentParser(description='任務・艦マスターの手動編集GUI（localhost）')
    parser.add_argument('--port', type=int, default=0, help='ポート番号。0は空きポートを自動選択')
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--repo', type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args()
    editor = Editor(args.repo.resolve()); editor.snapshot()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), handler(editor, secrets.token_hex(32)))
    address = f'http://127.0.0.1:{server.server_port}/'
    print('マスター編集: '+address, flush=True)
    print('終了するときは、このウィンドウでCtrl+Cを押してください。', flush=True)
    if not args.no_browser: webbrowser.open(address)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()


if __name__ == '__main__': main()
