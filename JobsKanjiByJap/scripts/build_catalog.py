"""从 EDRDG 原始数据生成可审计离线词库；--refresh 联网更新。Created by Jobs."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from jobs_kanji_by_jap.linguistics import ruby_parts

SOURCES = {
    'kanjidic2.xml.gz': 'https://www.edrdg.org/kanjidic/kanjidic2.xml.gz',
    'JMdict_e_examp.gz': 'https://www.edrdg.org/pub/Nihongo/JMdict_e_examp.gz',
}
LANG = '{http://www.w3.org/XML/1998/namespace}lang'


def dump(value):
    return json.dumps(value, ensure_ascii=False)


def texts(element, path):
    return [n.text or '' for n in element.findall(path)]


def download(url, path):
    temp = path.with_suffix('.download')
    print('下载：', url, flush=True)
    with urllib.request.urlopen(url, timeout=90) as response, temp.open('wb') as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
    with gzip.open(temp) as stream:
        while stream.read(1024 * 1024):
            pass
    temp.replace(path)


def build(cache, destination):
    from sudachipy import dictionary, tokenizer
    analyzer = dictionary.Dictionary().tokenizer()
    sentence_cache = {}

    def tokens(sentence):
        if sentence not in sentence_cache:
            sentence_cache[sentence] = [part for token in analyzer.tokenize(sentence, tokenizer.Tokenizer.SplitMode.C)
                                       for part in ruby_parts(token.surface(), token.reading_form())]
        return sentence_cache[sentence]

    temporary = destination.with_suffix('.building.sqlite')
    if temporary.exists():
        temporary.unlink()
    db = sqlite3.connect(temporary)
    db.executescript('''
    CREATE TABLE kanji (literal TEXT PRIMARY KEY, grade INTEGER, strokes INTEGER, freq INTEGER, data TEXT);
    CREATE TABLE words (id INTEGER PRIMARY KEY, priority INTEGER, data TEXT);
    CREATE TABLE forms (word_id INTEGER, spelling TEXT, reading TEXT);
    CREATE TABLE kanji_words (literal TEXT, word_id INTEGER, PRIMARY KEY(literal,word_id));
    CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
    ''')
    counts = {'kanji': 0, 'kanji_without_readings': 0, 'kanji_without_meanings': 0,
              'words': 0, 'words_with_examples': 0, 'sense_examples': 0}
    known = set()
    with gzip.open(cache / 'kanjidic2.xml.gz') as source:
        for _, node in ET.iterparse(source, events=['end']):
            if node.tag != 'character':
                continue
            literal = node.findtext('literal')
            readings = [{'text': r.text, 'type': r.get('r_type'), 'status': r.get('r_status', ''), 'on_type': r.get('on_type', '')}
                        for r in node.findall('reading_meaning/rmgroup/reading') if r.get('r_type') in ['ja_on', 'ja_kun']]
            meanings = [m.text for m in node.findall('reading_meaning/rmgroup/meaning') if m.get('m_lang', 'en') == 'en']
            names = texts(node, 'reading_meaning/nanori')
            data = {'literal': literal, 'readings': readings, 'nanori': names, 'meanings': meanings}
            db.execute('INSERT INTO kanji VALUES (?,?,?,?,?)',
                       (literal, int(node.findtext('misc/grade', '0')), int(node.findtext('misc/stroke_count', '0')),
                        int(node.findtext('misc/freq', '99999')), dump(data)))
            known.add(literal)
            counts['kanji'] += 1
            counts['kanji_without_readings'] += not (readings or names)
            counts['kanji_without_meanings'] += not bool(meanings)
            node.clear()
    with gzip.open(cache / 'JMdict_e_examp.gz') as source:
        for _, node in ET.iterparse(source, events=['end']):
            if node.tag != 'entry':
                continue
            entry_id = int(node.findtext('ent_seq'))
            spellings = texts(node, 'k_ele/keb')
            readings = [{'text': r.findtext('reb'), 'restr': texts(r, 're_restr'), 'no_kanji': r.find('re_nokanji') is not None,
                         'info': texts(r, 're_inf')} for r in node.findall('r_ele')]
            priority = int(not bool(node.findall('k_ele/ke_pri') or node.findall('r_ele/re_pri')))
            senses, previous_pos = [], []
            for s in node.findall('sense'):
                pos = texts(s, 'pos') or previous_pos
                previous_pos = pos
                examples = []
                for ex in s.findall('example'):
                    sentences = {n.get(LANG): n.text or '' for n in ex.findall('ex_sent')}
                    jp = sentences.get('jpn', '')
                    if jp:
                        examples.append({'jp': jp, 'en': sentences.get('eng', ''), 'tokens': tokens(jp),
                                         'source': ex.findtext('ex_srce', ''), 'form': ex.findtext('ex_text', '')})
                senses.append({'pos': pos, 'stagk': texts(s, 'stagk'), 'stagr': texts(s, 'stagr'),
                               'gloss': texts(s, 'gloss'), 'info': texts(s, 's_inf') + texts(s, 'misc') + texts(s, 'field') + texts(s, 'dial'),
                               'examples': examples})
            entry = {'spellings': spellings, 'readings': readings, 'senses': senses}
            db.execute('INSERT INTO words VALUES (?,?,?)', (entry_id, priority, dump(entry)))
            for reading in readings:
                valid = [''] if reading['no_kanji'] or not spellings else reading['restr'] or spellings
                db.executemany('INSERT INTO forms VALUES (?,?,?)', [(entry_id, spelling, reading['text']) for spelling in valid])
            db.executemany('INSERT INTO kanji_words VALUES (?,?)', [(ch, entry_id) for ch in set(''.join(spellings)) & known])
            counts['words'] += 1
            ex_count = sum(len(s['examples']) for s in senses)
            counts['words_with_examples'] += ex_count > 0
            counts['sense_examples'] += ex_count
            if counts['words'] % 25000 == 0:
                print('已导入词条：', counts['words'], flush=True)
            node.clear()
    db.executescript('CREATE INDEX forms_word ON forms(word_id); CREATE INDEX forms_spelling ON forms(spelling); CREATE INDEX forms_reading ON forms(reading);')
    counts['unique_sentences'] = len(sentence_cache)
    counts['sentences_with_unknown_ruby'] = sum(any(r == '未识别' for _, r in t) for t in sentence_cache.values())
    counts['kanji_without_words'] = db.execute('SELECT count(*) FROM kanji k WHERE NOT EXISTS (SELECT 1 FROM kanji_words w WHERE w.literal=k.literal)').fetchone()[0]
    counts['kanji_with_examples'] = db.execute("SELECT count(DISTINCT k.literal) FROM kanji_words k JOIN words w ON w.id=k.word_id WHERE w.data LIKE '%\"jp\":%'").fetchone()[0]
    report = {'built_at': datetime.now(timezone.utc).isoformat(), 'counts': counts,
              'sources': [{'file': name, 'url': url, 'sha256': hashlib.sha256((cache / name).read_bytes()).hexdigest()} for name, url in SOURCES.items()],
              'limits': ['覆盖 KANJIDIC2 收录的 JIS 汉字，不等于所有历史字、异体字、专名和读法。',
                         '未把词语读音强行分配给单个汉字；例句属于词义，不保证展示的每个读音都适用于该例句。',
                         '批量振假名由 Sudachi 自动生成，存在歧义；常见多音词另附人工编写学习示例。',
                         '学习界面仅显示中文与日文；中文字义预制，词义和例句译文按需在本机翻译并缓存，机器翻译未全量人工校对。']}
    manifest = destination.with_name('translation_manifest.json')
    if manifest.exists():
        report['translation'] = json.loads(manifest.read_text(encoding='utf-8'))
    db.execute('INSERT INTO meta VALUES (?,?)', ('coverage', dump(report)))
    db.commit()
    assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    db.close()
    temporary.replace(destination)
    destination.with_name('coverage.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(dump(counts), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=ROOT / 'work' / 'downloads')
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    for name, url in SOURCES.items():
        if args.refresh or not (args.cache / name).exists():
            download(url, args.cache / name)
    build(args.cache, ROOT / 'src/jobs_kanji_by_jap/assets/catalog.sqlite')


if __name__ == '__main__':
    main()
