"""保留词语读法，不把熟字训强行拆成单字读音。Created by Jobs."""
import re

HAN = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U000323af々〆〇]')


def hiragana(text):
    return ''.join(chr(ord(c) - 0x60) if '\u30a1' <= c <= '\u30f6' else c for c in text)


def spoken_reading(text):
    return hiragana(text.replace('.', '').replace('-', ''))


def ruby_parts(surface, reading):
    """只剥离确定相同的首尾假名；中间连写汉字使用词级振假名。"""
    reading = hiragana(reading)
    if not HAN.search(surface):
        return [(surface, '')]
    if not reading or HAN.search(reading):
        return [(surface, '未识别')]
    prefix = 0
    while prefix < min(len(surface), len(reading)) and not HAN.search(surface[prefix]) and hiragana(surface[prefix]) == reading[prefix]:
        prefix += 1
    tail = 0
    while tail < min(len(surface) - prefix, len(reading) - prefix) and not HAN.search(surface[-tail-1]) and hiragana(surface[-tail-1]) == reading[-tail-1]:
        tail += 1
    stop_s = len(surface) - tail
    stop_r = len(reading) - tail
    result = []
    if prefix:
        result.append((surface[:prefix], ''))
    result.append((surface[prefix:stop_s], reading[prefix:stop_r]))
    if tail:
        result.append((surface[stop_s:], ''))
    return result


def allowed_senses(entry, spelling, reading):
    return [s for s in entry['senses'] if
            (not s['stagk'] or spelling in s['stagk']) and
            (not s['stagr'] or reading in s['stagr'])]
