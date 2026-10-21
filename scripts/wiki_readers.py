"""Conservative Wiki table readers. Standard library only; never execute Wiki content."""
import html
import re
import unicodedata
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse


def clean(value):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', html.unescape(value))).strip()


def identity(value):
    return re.sub(r'[\s「」『』!！?？、。・"“”]', '', clean(value))


class Tables(HTMLParser):
    """Expand spans inside each table; nested tables are intentionally excluded."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self.links = [], []
        self.depth = self.skip = 0
        self.rows = self.row = self.cell = None
        self.attrs = {}; self.href = None; self.link_text = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('script', 'style', 'sup'): self.skip += 1
        if tag == 'a': self.href = a.get('href'); self.link_text = []
        if tag == 'table':
            self.depth += 1
            if self.depth == 1: self.rows = []
        if self.depth != 1: return
        if tag == 'tr': self.row = []
        elif tag in ('td', 'th') and self.row is not None:
            self.cell = []; self.attrs = a
        elif tag == 'br' and self.cell is not None: self.cell.append(' ')

    def handle_data(self, value):
        if self.skip: return
        if self.href is not None: self.link_text.append(value)
        if self.depth == 1 and self.cell is not None: self.cell.append(value)

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'sup'): self.skip = max(0, self.skip-1)
        if tag == 'a' and self.href is not None:
            self.links.append((self.href, clean(''.join(self.link_text)))); self.href = None
        if self.depth == 1:
            if tag in ('td', 'th') and self.cell is not None:
                span = lambda k: max(1, min(100, int(self.attrs.get(k, '1'))))
                self.row.append((clean(''.join(self.cell)), span('rowspan'), span('colspan')))
                self.cell = None
            elif tag == 'tr' and self.row is not None:
                self.rows.append(self.row); self.row = None
            elif tag == 'table': self.tables.append(self.expand(self.rows))
        if tag == 'table': self.depth = max(0, self.depth-1)

    @staticmethod
    def expand(rows):
        pending = {}; result = []
        for cells in rows:
            row = {}; following = {}
            for col, (text, remaining) in pending.items():
                row[col] = text
                if remaining > 1: following[col] = (text, remaining-1)
            col = 0
            for text, rowspan, colspan in cells:
                while col in row: col += 1
                for i in range(colspan):
                    row[col+i] = text
                    if rowspan > 1: following[col+i] = (text, rowspan-1)
                col += colspan
            result.append([row.get(i, '') for i in range(max(row, default=-1)+1)])
            pending = following
        return result


def read_tables(text):
    if '<table' in text.lower():
        parser = Tables(); parser.feed(text); return parser.tables, parser.links
    # Saved PukiWiki source. Spanning cells remain empty: ambiguity is not guessed.
    rows = []
    for line in text.splitlines():
        if not line.strip().startswith('|'): continue
        cells = line.strip().split('|')[1:-1]
        cells = [re.sub(r'\[\[([^]>]+)(?:>[^]]+)?\]\]', r'\1', c) for c in cells]
        cells = [clean(re.sub(r"(?:&br;|<br\s*/?>)", ' ', c).strip('~')) for c in cells]
        if cells: rows.append(cells)
    return [rows], []


def exact_number(value, maximum=100000):
    value = clean(value).replace(',', '')
    return int(value) if re.fullmatch(r'\d+', value) and int(value) <= maximum else None


def pair(value):
    m = re.fullmatch(r'(\d+)\s*/\s*(\d+)', clean(value))
    if not m: return None
    lo, hi = map(int, m.groups())
    return [lo, lo, hi] if 0 <= lo <= hi < 9999 else None


def parse(text, source):
    tables, links = read_tables(text)
    kind = source['kind']; records = []; warnings = []
    if kind == 'links':
        for href, name in links:
            url = urljoin(source['url'], href)
            if name and urlparse(url).hostname == urlparse(source['url']).hostname:
                records.append(dict(kind='link', name=name, url=url.split('#')[0]))
        return records, warnings
    if kind == 'quests':
        for rows in tables:
            for row in rows:
                if len(row) < 3 or not re.fullmatch(r'(?:[A-Z][A-Za-z]*|\d{2,8}[A-Za-z]+)\d+', row[0]): continue
                if row[2] in ('~', '↑', '>'): continue
                if any(t in row[2] for t in ('IDを', '表に移動', 'Moved to', 'Renumbered')): continue
                records.append(dict(kind='quest', wikiId=row[0], name=row[1], description=row[2]))
    elif kind == 'friendly':
        for rows in tables:
            flat = ' '.join(c for row in rows for c in row)
            if not ('回避' in flat and '対潜' in flat or 'Evasion' in flat and 'ASW' in flat): continue
            stats = {}
            for row in rows:
                for i, cell in enumerate(row[:-1]):
                    label = cell.strip('~').lower()
                    if label in ('回避', 'evasion'): stats['evasion'] = pair(row[i+1])
                    if label in ('対潜', 'asw'): stats['asw'] = pair(row[i+1])
            records.append(dict(kind='friendly', name=source.get('name', ''), id=source.get('shipId'), **stats))
            break
    elif kind == 'enemies':
        for rows in tables:
            hp_index = None; id_index = None
            for row in rows:
                labels = [clean(x).lower() for x in row]
                if any(x in labels for x in ('耐久', 'hp')) and labels and labels[0] in ('no.', 'id', 'api id'):
                    hp_index = next(i for i,x in enumerate(labels) if x in ('耐久', 'hp')); id_index=0; continue
                if hp_index is None or len(row) <= hp_index: continue
                ship = exact_number(row[id_index]); hp = exact_number(row[hp_index])
                if ship is None or ship < 1500: continue
                record = dict(kind='enemy', id=ship, name=row[1] if len(row)>1 else '', hp=hp if hp and hp>0 else None)
                # Only explicitly labelled per-slot counts, never total plane capacity.
                records.append(record)
    else: raise ValueError('Unsupported source kind: '+kind)
    if not records: warnings.append('対応する表が見つかりません。ページ構造・未確定値を確認してください。')
    return records, warnings


TYPES = {'海防艦':1, '駆逐艦':2, '軽巡洋艦':3, '軽巡':3, '重雷装巡洋艦':4, '重巡洋艦':5,
         '航空巡洋艦':6, '軽空母':7, '戦艦':9, '航空戦艦':10, '正規空母':11, '潜水艦':13, '潜水空母':14,
         '補給艦':15, '装甲空母':18, '練習巡洋艦':21}


def draft_counter(description):
    """Suggestions only. Every condition still requires human approval against the full Wiki row."""
    text = clean(description); target = re.search(r'(\d+)\s*(?:回|隻)', text)
    if not target: return None
    n = int(target[1])
    if not 1 <= n <= 100000: return None
    if '遠征' in text and '成功' in text:
        return dict(format='native', tasks=[dict(event='mission',target=n,ids=[],rank='E',materialTypes=[],required=0)])
    if any(w in text for w in ('撃沈','轟沈')):
        ids = next((v for k,v in [('補給艦',[15]),('潜水艦',[13,14]),('空母',[7,11,18])] if k in text), None)
        if ids: return dict(format='native',tasks=[dict(event='sink',target=n,ids=ids,rank='E',materialTypes=[],required=0)])
    rank = next((r for r in ('S','A','B') if re.search(r+r'\s*(?:勝利|判定)', text)), 'B')
    if '演習' in text and '勝利' in text: return dict(format='catalog',tasks=[dict(kind='practice',rank=rank,target=n)])
    maps = list(dict.fromkeys((int(a),int(b)) for a,b in re.findall(r'(?<!\d)(\d{1,2})-(\d)(?!\d)',text)))
    if maps and ('ボス' in text or '主力' in text) and '勝利' in text:
        return dict(format='catalog',tasks=[dict(kind='bossBattle',map=dict(area=a,number=b),rank=rank,target=n) for a,b in maps])
    return None


def draft_formation(description):
    conditions=[]
    for name, minimum in re.findall(r'(海防艦|駆逐艦|軽巡洋艦|重巡洋艦|正規空母|潜水艦)\s*(\d+)隻以上',clean(description)):
        conditions.append(dict(op='count',min=int(minimum),selector=dict(op='type',values=[TYPES[name]])))
    return dict(op='all',conditions=conditions) if conditions else None
