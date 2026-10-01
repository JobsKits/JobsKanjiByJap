"""本机中文释义：离线模型、持久缓存及不回退英文的显示边界。Created by Jobs."""
from pathlib import Path
import re
import sqlite3

ASSETS = Path(__file__).resolve().parent / 'assets'
MODEL = ASSETS / 'translation/en_zh'
VERSION = 'argos-en-zh-1.9-jobs-2'

EXACT = {
    'water': '水', 'mountain': '山', 'river': '河流', 'tree': '树木',
    'read': '读；阅读', 'eat; food': '吃；食物',
    'stream; river; river or three-stroke river radical (no. 47)': '溪流；河川；川字部或三点水部首（第47部）',
    'going; journey; carry out; conduct; act; line; row; bank': '去；行程；实行；行为；行列',
    'see; hopes; chances; idea; opinion; look at; visible': '看见；希望；机会；想法；意见；观看；可见的',
    'to eat': '吃；食用', 'to drink': '喝；饮用', 'to read': '读；阅读',
    'to live on (e.g. a salary); to live off; to subsist on': '靠……生活；以……为生',
    'You should eat more fruit.': '应该多吃些水果。',
    'I am determined to make a living as a playwright.': '我下定决心要以写剧本为生。',
    'life; genuine; birth': '生命；未经加工；出生',
}
POS = {
    'unclassified': '未分类', 'noun (common) (futsuumeishi)': '普通名词',
    'expressions (phrases, clauses, etc.)': '固定表达（短语、分句等）',
    'adjectival nouns or quasi-adjectives (keiyodoshi)': '形容动词（な形容词）',
    "nouns which may take the genitive case particle 'no'": '可接「の」的名词',
    'adjective (keiyoushi)': '形容词（い形容词）', 'transitive verb': '他动词',
    'pronoun': '代词', 'adverb (fukushi)': '副词', "adverb taking the 'to' particle": '可接「と」的副词',
    'noun or participle which takes the aux. verb suru': '可接「する」的名词',
    'pre-noun adjectival (rentaishi)': '连体词', 'interjection (kandoushi)': '感叹词',
    'Ichidan verb': '一段动词', 'intransitive verb': '自动词',
    'Godan verb - -aru special class': '五段动词（ある特殊活用）', 'auxiliary verb': '补助动词',
    'noun or verb acting prenominally': '用作连体修饰的名词或动词',
    'conjunction': '接续词', 'particle': '助词', 'noun, used as a suffix': '名词性后缀',
    'prefix': '前缀', 'suffix': '后缀', 'suru verb - included': '含「する」的动词',
    "'taru' adjective": 'タリ活用形容动词', 'adjective (keiyoushi) - yoi/ii class': '形容词（よい／いい类）',
    'auxiliary': '助动词', 'copula': '断定助动词', 'Kuru verb - special class': 'カ行动词（来る特殊活用）',
    'auxiliary adjective': '补助形容词', 'noun, used as a prefix': '名词性前缀',
    'counter': '量词／助数词', 'numeric': '数词', 'suru verb - special class': 'サ行动词（する特殊活用）',
    "'shiku' adjective (archaic)": 'シク活用形容词（古语）', 'Godan verb - Iku/Yuku special class': '五段动词（行く／ゆく特殊活用）',
    'Ichidan verb - zuru verb (alternative form of -jiru verbs)': '一段动词（ずる形，对应じる形）',
    'su verb - precursor to the modern suru': 'サ行变格动词（古语「す」）',
    'Ichidan verb - kureru special class': '一段动词（くれる特殊活用）',
    "'ku' adjective (archaic)": 'ク活用形容词（古语）',
    'irregular ru verb, plain form ends with -ri': 'ラ行变格动词（终止形为り）',
    'archaic/formal form of na-adjective': '形容动词的古语／正式形式',
    'irregular nu verb': 'ナ行变格动词', 'verb unspecified': '动词（活用类型未标注）',
}
ENDING = dict(u='う', su='す', ku='く', ru='る', mu='む', gu='ぐ', tsu='つ', bu='ぶ', nu='ぬ', yu='ゆ', dzu='づ', zu='ず', **{'hu/fu': 'ふ'})


def pos_zh(tag):
    if tag in POS:
        return POS[tag]
    ending = re.search(r"with '([^']+)' ending", tag)
    if ending and ending[1] in ENDING:
        if tag.startswith('Godan'):
            family = '五段动词'
        elif tag.startswith('Yodan'):
            family = '四段动词（古语）'
        elif tag.startswith('Nidan'):
            family = '上二段动词（古语）' if '(upper class)' in tag else '下二段动词（古语）' if '(lower class)' in tag else '二段动词（古语）'
        else:
            return '词性暂未完成中文标注'
        extra = '，特殊活用' if 'special class' in tag or 'irregular' in tag else ''
        extra += '，ゑ活用' if "'we' conjugation" in tag else ''
        return f'{family}（{ENDING[ending[1]]}结尾{extra}）'
    return '词性暂未完成中文标注'


def display_translation(value):
    value = value.replace('▁', '').replace(';', '；').strip()
    value = re.sub(r'；[\s；]*', '；', value)
    pieces = [p.strip() for p in value.split('；') if p.strip()]
    value = '；'.join(dict.fromkeys(pieces))
    repeated = re.split(r'[,，、]', value)
    if len(repeated) > 2 and len(set(p.strip() for p in repeated if p.strip())) == 1:
        value = repeated[0].strip()
    if not value or not re.search(r'[\u3400-\u9fff]', value):
        raise ValueError('未能生成可靠中文译文')
    # 未被翻译的英文长句不可作为成功结果回到学习界面。
    if re.search(r'[A-Za-z]', value):
        raise ValueError('译文仍有未处理的外语说明')
    return value


class LocalChinese:
    def __init__(self, cache_path):
        self.cache_path = Path(cache_path)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.cache_path)
        self.db.execute('CREATE TABLE IF NOT EXISTS translations (version TEXT, source TEXT, zh TEXT, PRIMARY KEY(version,source))')
        self.db.commit()
        seed = ASSETS / 'chinese_seed.sqlite'
        self.seed = sqlite3.connect(seed.resolve().as_uri() + '?mode=ro', uri=True) if seed.exists() and seed.resolve() != self.cache_path.resolve() else None
        self.model = None
        self.tokenizer = None

    def cached(self, source):
        if source in EXACT:
            return EXACT[source]
        if source in POS:
            return POS[source]
        for connection in (self.db, self.seed):
            if connection:
                row = connection.execute('SELECT zh FROM translations WHERE version=? AND source=?', (VERSION, source)).fetchone()
                if row:
                    try:
                        return display_translation(row[0])
                    except ValueError:
                        return None
        return None

    def translate(self, sources):
        sources = list(dict.fromkeys(s for s in sources if s))
        results = {s: self.cached(s) for s in sources}
        missing = [s for s in sources if results[s] is None]
        if missing:
            import ctranslate2
            import sentencepiece
            if self.model is None:
                self.tokenizer = sentencepiece.SentencePieceProcessor(model_file=str(MODEL / 'sentencepiece.model'))
                self.model = ctranslate2.Translator(str(MODEL / 'model'), device='cpu', compute_type='int8', intra_threads=4)
            # 分段后重新组合，避免长义项被解码长度静默截断。
            chunks, owners = [], []
            for source in missing:
                parts = re.split(r'(?<=[.!?;])\s+', source)
                for part in parts:
                    tokens = self.tokenizer.encode(part, out_type=str)
                    for start in range(0, len(tokens), 128):
                        chunks.append(tokens[start:start+128])
                        owners.append(source)
            outputs = self.model.translate_batch(chunks, beam_size=4, max_batch_size=16,
                                                  max_decoding_length=256, replace_unknowns=True,
                                                  length_penalty=0.2, no_repeat_ngram_size=3, repetition_penalty=1.1)
            translated = {s: [] for s in missing}
            for source, output in zip(owners, outputs):
                translated[source].append(self.tokenizer.decode(output.hypotheses[0]).replace('▁', '').strip())
            for source in missing:
                try:
                    zh = display_translation('；'.join(translated[source]))
                except ValueError:
                    zh = '中文译文待校对'
                results[source] = zh
                self.db.execute('INSERT OR REPLACE INTO translations VALUES (?,?,?)', (VERSION, source, zh))
            self.db.commit()
        return results

    def close(self):
        self.db.close()
        if self.seed:
            self.seed.close()
