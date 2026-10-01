"""预制汉字中文释义及反查索引；运行时按需翻译其余词义。Created by Jobs."""
import json
from pathlib import Path
import sqlite3
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from jobs_kanji_by_jap.chinese import LocalChinese, ASSETS


def main():
    engine = LocalChinese(ASSETS / 'chinese_seed.sqlite')
    engine.db.execute('CREATE TABLE IF NOT EXISTS kanji_zh (literal TEXT PRIMARY KEY, zh TEXT)')
    source = sqlite3.connect((ASSETS / 'catalog.sqlite').as_uri() + '?mode=ro', uri=True)
    rows = source.execute('SELECT literal,data FROM kanji ORDER BY freq').fetchall()
    start = time.monotonic()
    for offset in range(0, len(rows), 64):
        batch = rows[offset:offset+64]
        meanings = [(char, '; '.join(json.loads(data)['meanings'])) for char, data in batch]
        result = engine.translate([text for _, text in meanings])
        engine.db.executemany('INSERT OR REPLACE INTO kanji_zh VALUES (?,?)', [(char, result.get(text, '字库未收录释义')) for char,text in meanings])
        engine.db.commit()
        if offset % 512 == 0:
            print(f'{offset}/{len(rows)}  耗时 {time.monotonic()-start:.1f} 秒', flush=True)
    engine.close()
    source.close()


if __name__ == '__main__':
    main()
