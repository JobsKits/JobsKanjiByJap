"""只读 SQLite 查询，保留读音和义项适用范围。Created by Jobs."""
import json
import re
from pathlib import Path
import sqlite3
from .linguistics import hiragana

ASSETS = Path(__file__).resolve().parent / 'assets'


class Catalog:
    def __init__(self, path=None):
        self.db = sqlite3.connect((path or ASSETS / 'catalog.sqlite').resolve().as_uri() + '?mode=ro', uri=True)
        self.db.row_factory = sqlite3.Row
        seed = ASSETS / 'chinese_seed.sqlite'
        self.zh = sqlite3.connect(seed.as_uri() + '?mode=ro', uri=True) if seed.exists() else None
        self.coverage = json.loads(self.db.execute("SELECT value FROM meta WHERE key='coverage'").fetchone()[0])

    def search(self, query='', group=0):
        query = query.strip()
        clauses, args = [], []
        if group == 1:
            clauses.append('grade BETWEEN 1 AND 8')
        elif group == 2:
            clauses.append('grade IN (9,10)')
        if query:
            clauses.append('''(instr(?,literal)>0 OR instr(data,?)>0 OR literal IN (
                SELECT kw.literal FROM kanji_words kw JOIN forms f ON f.word_id=kw.word_id
                WHERE f.spelling=? OR f.reading=?))''')
            args.extend([query, hiragana(query), query, hiragana(query)])
            if self.zh and re.search(r'[\u3400-\u9fff]', query):
                matched = [r[0] for r in self.zh.execute('SELECT literal FROM kanji_zh WHERE instr(zh,?)>0', (query,))]
                if matched:
                    clauses[-1] = '(' + clauses[-1] + ' OR instr(?,literal)>0)'
                    args.append(''.join(matched))
        where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
        return self.db.execute('SELECT literal,grade,strokes FROM kanji' + where + ' ORDER BY freq,literal', args).fetchall()

    def kanji(self, literal):
        row = self.db.execute('SELECT * FROM kanji WHERE literal=?', (literal,)).fetchone()
        return dict(row) | json.loads(row['data'])

    def words(self, literal, query='', offset=0, limit=15):
        args = [literal]
        extra = ''
        if query:
            extra = ' AND EXISTS (SELECT 1 FROM forms f WHERE f.word_id=w.id AND (instr(f.spelling,?)>0 OR instr(f.reading,?)>0))'
            args.extend([query, hiragana(query)])
        base = ' FROM words w JOIN kanji_words k ON w.id=k.word_id WHERE k.literal=?' + extra
        count = self.db.execute('SELECT count(*)' + base, args).fetchone()[0]
        rows = self.db.execute('SELECT w.id,w.data' + base + ' ORDER BY w.priority, length(json_extract(w.data,\'$.spellings[0]\')),w.id LIMIT ? OFFSET ?', args + [limit, offset]).fetchall()
        return count, [(row['id'], json.loads(row['data'])) for row in rows]

    def close(self):
        self.db.close()
        if self.zh:
            self.zh.close()
