"""JobsKanjiByJap 原生双平台学习界面。Created by Jobs."""
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys

from PySide6.QtCore import Qt, QSize, QRectF, QTimer, QUrl, QStandardPaths
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QDesktopServices, QPalette
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, QListWidget, QListWidgetItem,
    QGridLayout, QScrollArea, QSplitter, QDialog, QTextBrowser, QMessageBox, QSlider, QSizePolicy)
from .catalog import Catalog, ASSETS
from .linguistics import spoken_reading, allowed_senses
from .speech import Speech
from .chinese import pos_zh
from .translation_ui import ChineseLabels

from .theme import ReadingTheme

KANA_IPA = {
    "あ": "a", "い": "i", "う": "ɯ", "え": "e", "お": "o",
    "か": "ka", "き": "ki", "く": "kɯ", "け": "ke", "こ": "ko",
    "さ": "sa", "し": "ɕi", "す": "sɯ", "せ": "se", "そ": "so",
    "た": "ta", "ち": "tɕi", "つ": "tsɯ", "て": "te", "と": "to",
    "な": "na", "に": "ni", "ぬ": "nɯ", "ね": "ne", "の": "no",
    "は": "ha", "ひ": "çi", "ふ": "ɸɯ", "へ": "he", "ほ": "ho",
    "ま": "ma", "み": "mi", "む": "mɯ", "め": "me", "も": "mo",
    "や": "ja", "ゆ": "jɯ", "よ": "jo",
    "ら": "ɾa", "り": "ɾi", "る": "ɾɯ", "れ": "ɾe", "ろ": "ɾo",
    "わ": "wa", "を": "o", "が": "ɡa", "ぎ": "ɡi", "ぐ": "ɡɯ",
    "げ": "ɡe", "ご": "ɡo", "ざ": "za", "じ": "dʑi", "ず": "zɯ",
    "ぜ": "ze", "ぞ": "zo", "だ": "da", "ぢ": "dʑi", "づ": "dzɯ",
    "で": "de", "ど": "do", "ば": "ba", "び": "bi", "ぶ": "bɯ",
    "べ": "be", "ぼ": "bo", "ぱ": "pa", "ぴ": "pi", "ぷ": "pɯ",
    "ぺ": "pe", "ぽ": "po", "ん": "ɴ",
}


def label(text, name='', wrap=True):
    item = QLabel(text)
    item.setTextFormat(Qt.TextFormat.PlainText)
    item.setWordWrap(wrap)
    item.setObjectName(name)
    item.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return item


def button(text, callback):
    item = QPushButton(text)
    item.setCursor(Qt.CursorShape.PointingHandCursor)
    item.clicked.connect(callback)
    return item


def clear(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().hide()
            item.widget().deleteLater()
        elif item.layout():
            clear(item.layout())


class Ruby(QWidget):
    """按词排版红色上标；保持熟字训整体，自动换行。"""
    def __init__(self, tokens, speak, parent=None):
        super().__init__(parent)
        self.tokens = tokens
        self.speak = speak
        self.base_font = QFont('Hiragino Sans' if sys.platform == 'darwin' else 'Yu Gothic', 20)
        self.ruby_font = QFont(self.base_font.family(), 11)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip('点击例句朗读。红字为词级振假名。')
        self.setAccessibleName(''.join(t[0] for t in tokens))

    def hasHeightForWidth(self):
        return True

    def arrange(self, width):
        base, ruby = QFontMetricsF(self.base_font), QFontMetricsF(self.ruby_font)
        x, y, result = 0.0, 0.0, []
        line = base.height() + ruby.height() + 14
        for surface, reading in self.tokens:
            w = max(base.horizontalAdvance(surface), ruby.horizontalAdvance(reading)) + 4
            if x and x + w > max(width, 1):
                x = 0
                y += line
            result.append((x, y, w, surface, reading))
            x += w
        return result, int(y + line + 4)

    def heightForWidth(self, width):
        return self.arrange(width)[1]

    def sizeHint(self):
        return QSize(550, self.heightForWidth(550))

    def resizeEvent(self, event):
        self.setMinimumHeight(self.heightForWidth(event.size().width()))
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        rh = QFontMetricsF(self.ruby_font).height()
        bh = QFontMetricsF(self.base_font).height()
        for x, y, w, surface, reading in self.arrange(self.width())[0]:
            painter.setFont(self.ruby_font)
            painter.setPen(QColor(QApplication.instance().property('rubyColor') or '#c52e38'))
            painter.drawText(QRectF(x, y, w, rh + 2), Qt.AlignmentFlag.AlignCenter, reading)
            painter.setFont(self.base_font)
            painter.setPen(self.palette().color(QPalette.ColorRole.WindowText))
            painter.drawText(QRectF(x, y + rh + 3, w, bh + 4), Qt.AlignmentFlag.AlignCenter, surface)
        painter.end()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # 假名点读防止系统再次猜测多音字；未识别部分保留原文。
            self.speak(''.join(r if r and r != '未识别' else s for s, r in self.tokens))


class Window(QMainWindow):
    PAGE = 15

    def __init__(self):
        super().__init__()
        self.catalog = Catalog()
        self.chinese = ChineseLabels(self)
        self.guides = json.loads((ASSETS / 'guides.json').read_text(encoding='utf-8'))
        self.speech = Speech(self)
        self.speech.message.connect(self.statusBar().showMessage)
        self.current = None
        self.offset = 0
        self.setWindowTitle('JobsKanjiByJap · 日语汉字点读')
        self.resize(1240, 870)
        self.setMinimumSize(860, 600)
        root = QWidget()
        outer = QVBoxLayout(root)
        outer.setContentsMargins(22, 20, 22, 12)
        top = QHBoxLayout()
        top.addWidget(label('漢字 / JobsKanjiByJap', 'brand'))
        top.addStretch()
        top.addWidget(label('主题', wrap=False))
        self.theme_switch = QComboBox()
        self.theme_switch.setAccessibleName('阅读主题')
        for title, mode in [('日间', 'light'), ('夜间', 'dark'), ('跟随系统', 'system')]:
            self.theme_switch.addItem(title, mode)
        theme = QApplication.instance().reading_theme
        self.theme_switch.setCurrentIndex(self.theme_switch.findData(theme.mode))
        self.theme_switch.currentIndexChanged.connect(
            lambda: theme.set_mode(self.theme_switch.currentData()))
        top.addWidget(self.theme_switch)
        top.addWidget(button('元音 · 辅音 · 元音＋辅音', self.show_kana))
        top.addWidget(button('数据覆盖与使用说明', self.about))
        outer.addLayout(top)
        outer.addWidget(label('把读音放回词语里理解。音读 · 训读 · 名乘 · 熟字训', 'muted'))
        split = QSplitter()
        sidebar = QWidget()
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(0, 12, 12, 0)
        self.search = QLineEdit()
        self.search.setPlaceholderText('汉字 / 日语词语 / 假名 / 中文字义')
        side.addWidget(self.search)
        self.group = QComboBox()
        self.group.addItems(['全部收录汉字', '常用汉字', '人名用汉字'])
        side.addWidget(self.group)
        self.count = label('', 'muted')
        side.addWidget(self.count)
        self.list = QListWidget()
        side.addWidget(self.list, 1)
        side.addWidget(label('日语语音', 'muted'))
        self.voices = QComboBox()
        for voice in self.speech.voices:
            self.voices.addItem(voice.name())
        if not self.speech.voices:
            self.voices.addItem('未安装日语语音 · 见使用说明')
        self.voices.currentIndexChanged.connect(self.speech.set_voice)
        side.addWidget(self.voices)
        speed = QHBoxLayout()
        speed.addWidget(label('语速'))
        self.speed = QSlider(Qt.Orientation.Horizontal)
        self.speed.setRange(-70, 30)
        self.speed.setValue(-15)
        self.speed.valueChanged.connect(lambda v: self.speech.engine.setRate(v / 100))
        speed.addWidget(self.speed)
        speed.addWidget(button('停止', self.speech.engine.stop))
        side.addLayout(speed)
        split.addWidget(sidebar)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.body = QWidget()
        self.content = QVBoxLayout(self.body)
        self.content.setSpacing(13)
        self.content.setContentsMargins(14, 12, 14, 12)
        self.scroll.setWidget(self.body)
        split.addWidget(self.scroll)
        split.setSizes([320, 880])
        outer.addWidget(split, 1)
        outer.addWidget(label('词典：EDRDG / KANJIDIC2 / JMdict · 例句：Tatoeba · CC BY-SA · 振假名为自动分析或学习示例', 'muted'))
        self.setCentralWidget(root)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self.refresh)
        self.search.textChanged.connect(lambda: self.timer.start())
        self.group.currentIndexChanged.connect(self.refresh)
        self.list.currentItemChanged.connect(self.select)
        self.refresh()
        items = self.list.findItems('生', Qt.MatchFlag.MatchStartsWith)
        if items:
            self.list.setCurrentItem(items[0])
        self.statusBar().showMessage('离线词库已就绪 · 点击读音或例句播放日语')

    def show_kana(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('日语基础发音 · 点击点读')
        dialog.resize(800, 760)
        outer = QVBoxLayout(dialog)
        outer.addWidget(label('上方元音、左侧辅音、内部组合都可点读。每格附 Hepburn 罗马字与宽式 IPA；辅音用代表音节试听。し shi、ち chi、つ tsu、ふ fu 为特殊读法；空格不生成组合。を读 o；ん的发音随语境变化。注音仅作入门提示。', 'muted'))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        grid = QGridLayout(body)
        grid.addWidget(label('辅音 / 元音'), 0, 0)
        for column, (kana, roman) in enumerate(zip('あいうえお', ('a', 'i', 'u', 'e', 'o')), 1):
            grid.addWidget(button(f'{kana}\n{roman} /{KANA_IPA[kana]}/', lambda checked=False, text=kana: self.speech.say(text)), 0, column)
        rows = [('k', 'かきくけこ', ['ka', 'ki', 'ku', 'ke', 'ko']), ('s', 'さしすせそ', ['sa', 'shi', 'su', 'se', 'so']), ('t', 'たちつてと', ['ta', 'chi', 'tsu', 'te', 'to']), ('n', 'なにぬねの', ['na', 'ni', 'nu', 'ne', 'no']), ('h', 'はひふへほ', ['ha', 'hi', 'fu', 'he', 'ho']), ('m', 'まみむめも', ['ma', 'mi', 'mu', 'me', 'mo']), ('y', 'や ゆ よ', ['ya', '', 'yu', '', 'yo']), ('r', 'らりるれろ', ['ra', 'ri', 'ru', 're', 'ro']), ('w', 'わ   を', ['wa', '', '', '', 'o']), ('g', 'がぎぐげご', ['ga', 'gi', 'gu', 'ge', 'go']), ('z', 'ざじずぜぞ', ['za', 'ji', 'zu', 'ze', 'zo']), ('d', 'だぢづでど', ['da', 'ji', 'zu', 'de', 'do']), ('b', 'ばびぶべぼ', ['ba', 'bi', 'bu', 'be', 'bo']), ('p', 'ぱぴぷぺぽ', ['pa', 'pi', 'pu', 'pe', 'po'])]
        for row, (consonant, kana, readings) in enumerate(rows, 1):
            grid.addWidget(button(f'{consonant} 行 / {kana[0]}\n{readings[0]} /{KANA_IPA[kana[0]]}/', lambda checked=False, text=kana[0]: self.speech.say(text)), row, 0)
            for column, (text, roman) in enumerate(zip(kana, readings), 1):
                if roman:
                    katakana = chr(ord(text) + 0x60)
                    grid.addWidget(button(f'{text} {katakana}\n{roman} /{KANA_IPA[text]}/', lambda checked=False, text=text: self.speech.say(text)), row, column)
                else:
                    grid.addWidget(label('—'), row, column)
        grid.addWidget(button('ん ン\nn /ɴ/ · 鼻音', lambda: self.speech.say('ん')), len(rows) + 1, 0, 1, 6)
        scroll.setWidget(body)
        outer.addWidget(scroll)
        outer.addWidget(button('停止', self.speech.engine.stop))
        dialog.finished.connect(self.speech.engine.stop)
        dialog.exec()

    def refresh(self):
        rows = self.catalog.search(self.search.text(), self.group.currentIndex())
        self.list.blockSignals(True)
        self.list.clear()
        for row in rows:
            item = QListWidgetItem(f"{row['literal']}     {row['strokes']} 画")
            item.setData(Qt.ItemDataRole.UserRole, row['literal'])
            self.list.addItem(item)
        self.list.blockSignals(False)
        self.count.setText(f'找到 {len(rows):,} 字 / 共 {self.catalog.coverage["counts"]["kanji"]:,} 字')
        if rows:
            self.list.setCurrentRow(0)
        else:
            clear(self.content)
            self.content.addWidget(label('没有匹配结果。此字可能不在当前字库中；不能据此推断它没有日语读音。', 'notice'))
            self.content.addStretch()

    def select(self, item, previous=None):
        if not item:
            return
        self.current = item.data(Qt.ItemDataRole.UserRole)
        self.offset = 0
        self.show_kanji()

    def card(self, parent):
        widget = QWidget()
        widget.setObjectName('card')
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(9)
        parent.addWidget(widget)
        return layout

    def zh_label(self, sources, name='', prefix='', suffix=''):
        item = label('', name)
        self.chinese.bind(item, sources, prefix, suffix)
        return item

    def readings(self, title, values, parent):
        parent.addWidget(label(title, 'muted'))
        if not values:
            parent.addWidget(label('字库未收录', 'muted'))
            return
        # 每行少量按钮，窄窗口不截断多读音。
        for start in range(0, len(values), 4):
            row = QHBoxLayout()
            for text in values[start:start+4]:
                b = button(text, lambda checked=False, t=text: self.speech.say(spoken_reading(t)))
                b.setToolTip('点击发音：' + spoken_reading(text))
                row.addWidget(b)
            row.addStretch()
            parent.addLayout(row)

    def show_kanji(self):
        clear(self.content)
        data = self.catalog.kanji(self.current)
        header = self.card(self.content)
        row = QHBoxLayout()
        row.addWidget(label(self.current, 'kanji'))
        meanings = QVBoxLayout()
        guide = self.guides.get(self.current, {})
        if guide:
            meanings.addWidget(label('中文学习提示：' + guide['meaning'], 'heading'))
        meanings.addWidget(self.zh_label(['; '.join(data['meanings'])], prefix='字义：', suffix='（机器翻译）'))
        meanings.addWidget(label(f"{data['strokes']} 画 · Unicode U+{ord(self.current):04X} · KANJIDIC2", 'muted'))
        row.addLayout(meanings, 1)
        header.addLayout(row)
        for kind, title in [('ja_on', '音读'), ('ja_kun', '训读')]:
            values = list(dict.fromkeys(r['text'] for r in data['readings'] if r['type'] == kind))
            self.readings(title, values, header)
        self.readings('名乘（人名读法；不代表所有人名）', data['nanori'], header)
        marks = {'jy': '常用读音', 'kan': '汉音', 'go': '吴音', 'tou': '唐音', "kan'you": '惯用音'}
        notes = [r['text'] + '：' + ' / '.join(marks.get(v, '其他字典标记') for v in [r['status'], r['on_type']] if v) for r in data['readings'] if r['status'] or r['on_type']]
        if notes:
            header.addWidget(label('原词典读音标记：' + '；'.join(notes), 'muted'))
        header.addWidget(label('「.」后是送假名，「-」表示接续位置；播放时读完整假名。单字读音不自动等于任意词语中的读法。', 'muted'))
        if guide:
            self.content.addWidget(label('多音字学习示例 · 中文讲解', 'heading'))
            for example in guide['examples']:
                box = self.card(self.content)
                box.addWidget(button(example['word'] + '  /  ' + example['reading'] + '  ·  ' + example['meaning'], lambda checked=False, t=example['reading']: self.speech.say(t)))
                box.addWidget(Ruby(example['tokens'], self.speech.say))
                box.addWidget(label(example['zh']))
                box.addWidget(label('原创学习示例 · 词级振假名', 'muted'))
        self.content.addWidget(label('词语、词性与例句', 'heading'))
        self.word_filter = QLineEdit()
        self.word_filter.setPlaceholderText('在含此字的词语中搜索，如 がくせい；按回车筛选')
        self.word_filter.returnPressed.connect(self.filter_words)
        self.content.addWidget(self.word_filter)
        self.words_widget = QWidget()
        self.words_layout = QVBoxLayout(self.words_widget)
        self.words_layout.setContentsMargins(0, 0, 0, 0)
        self.content.addWidget(self.words_widget)
        self.content.addStretch()
        self.show_words()
        self.scroll.verticalScrollBar().setValue(0)

    def filter_words(self):
        self.offset = 0
        self.show_words()

    def show_words(self):
        clear(self.words_layout)
        count, entries = self.catalog.words(self.current, self.word_filter.text().strip(), self.offset, self.PAGE)
        self.words_layout.addWidget(label(f'共 {count:,} 个词条 · 当前 {self.offset+1 if count else 0}–{min(self.offset+self.PAGE,count)}', 'muted'))
        if not entries:
            self.words_layout.addWidget(label('没有收录匹配词语和例句。未用自动造句填补词库缺项。', 'notice'))
        for word_id, entry in entries:
            box = self.card(self.words_layout)
            spellings = [s for s in entry['spellings'] if self.current in s]
            box.addWidget(label(' / '.join(spellings), 'heading'))
            box.addWidget(label('点击下方词语读法，查看该写法和读法适用的词义与例句。', 'muted'))
            for reading in entry['readings']:
                if reading['no_kanji']:
                    continue
                valid = [s for s in spellings if not reading['restr'] or s in reading['restr']]
                if not valid:
                    continue
                for spelling in valid:
                    row = QHBoxLayout()
                    row.addWidget(button(spelling + '  ' + reading['text'], lambda checked=False, t=reading['text']: self.speech.say(t)))
                    row.addWidget(button('词义 / 例句', lambda checked=False, e=entry, s=spelling, r=reading['text']: self.word_detail(e, s, r)))
                    row.addStretch()
                    box.addLayout(row)
                if reading['info']:
                    box.addWidget(self.zh_label(reading['info'], 'muted', prefix='读法标记：'))
            first = entry['senses'][0] if entry['senses'] else {}
            box.addWidget(self.zh_label(['; '.join(first.get('gloss', []))], prefix='中文释义：', suffix='（机器翻译，具体读法见详情）'))
        nav = QHBoxLayout()
        prev = button('上一页', lambda: self.page(-1))
        prev.setEnabled(self.offset > 0)
        nxt = button('下一页', lambda: self.page(1))
        nxt.setEnabled(self.offset + self.PAGE < count)
        nav.addWidget(prev)
        nav.addWidget(nxt)
        nav.addStretch()
        self.words_layout.addLayout(nav)

    def page(self, delta):
        self.offset += delta * self.PAGE
        self.show_words()
        QTimer.singleShot(0, lambda: self.scroll.ensureWidgetVisible(self.word_filter))

    def word_detail(self, entry, spelling, reading):
        dialog = QDialog(self)
        dialog.setWindowTitle(spelling + ' · ' + reading)
        dialog.resize(820, 700)
        outer = QVBoxLayout(dialog)
        outer.addWidget(button(spelling + '  /  ' + reading + '  · 点击朗读', lambda: self.speech.say(reading)))
        outer.addWidget(label('中文释义和例句译文由本机离线模型生成，标注“机器翻译”的内容可能有误。例句按词义关联；红字为振假名。', 'notice'))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        layout = QVBoxLayout(body)
        for i, sense in enumerate(allowed_senses(entry, spelling, reading), 1):
            box = self.card(layout)
            box.addWidget(self.zh_label(['; '.join(sense['gloss'])], 'heading', prefix=f'{i}、', suffix='（机器翻译）'))
            box.addWidget(label('词性：' + ' / '.join(pos_zh(tag) for tag in sense['pos']), 'muted'))
            if sense['info']:
                box.addWidget(self.zh_label(sense['info'], 'muted', prefix='用法：', suffix='（机器翻译）'))
            if not sense['examples']:
                box.addWidget(label('这个词义尚无收录例句。', 'muted'))
            for ex in sense['examples']:
                box.addWidget(Ruby(ex['tokens'], self.speech.say))
                box.addWidget(self.zh_label([ex['en']], prefix='中文：', suffix='（机器翻译）'))
                if ex['source'].isdigit():
                    url = 'https://tatoeba.org/zh-cn/sentences/show/' + ex['source']
                    box.addWidget(button('Tatoeba 原句 / 作者 / 校对', lambda checked=False, u=url: QDesktopServices.openUrl(QUrl(u))))
        layout.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll)
        dialog.exec()

    def about(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('数据覆盖与使用说明')
        dialog.resize(780, 650)
        layout = QVBoxLayout(dialog)
        text = QTextBrowser()
        text.setOpenExternalLinks(True)
        counts = self.catalog.coverage['counts']
        count_names = {'kanji': '汉字', 'kanji_without_readings': '缺读音汉字', 'kanji_without_meanings': '原库缺释义汉字', 'words': '词条', 'words_with_examples': '有例句词条', 'sense_examples': '按词义收录例句', 'unique_sentences': '不同例句', 'sentences_with_unknown_ruby': '含未识别读音例句', 'kanji_without_words': '无关联词条汉字', 'kanji_with_examples': '有关联例句汉字'}
        count_text = '\n'.join(f'{count_names.get(k, "其他统计")}：{v:,}' for k,v in counts.items())
        text.setPlainText('数据覆盖\n\n' + count_text + '\n\n' +
            '\n'.join(self.catalog.coverage['limits']) + '\n\n日语读音不仅取决于词性，还受词语、送假名、连浊、促音和熟字训影响。\n\n' +
            '发音：需要系统安装日语语音。macOS 在辅助功能的朗读内容设置中添加日语；Windows 在语言与语音设置中添加日语语音。安装后重启软件。合成语音不等于母语者录音，也未提供音调核验。\n\n' +
            '更新词库：关闭软件后，在工程运行 scripts/bootstrap.py update，再重新打包；仅按明确操作更新，不在后台联网。\n\n' +
            (ASSETS / 'NOTICE.txt').read_text(encoding='utf-8'))
        layout.addWidget(text)
        dialog.exec()

    def closeEvent(self, event):
        self.speech.engine.stop()
        self.catalog.close()
        self.chinese.close()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.reading_theme = ReadingTheme(app)
    app.setApplicationName('JobsKanjiByJap')
    app.setOrganizationName('Jobs')
    log_dir = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)) / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, handlers=[RotatingFileHandler(log_dir / 'app.log', maxBytes=1000000, backupCount=2, encoding='utf-8')])
    def report_error(kind, value, traceback):
        logging.error('界面异常', exc_info=(kind, value, traceback))
        QMessageBox.critical(None, 'JobsKanjiByJap', f'操作失败：{value}\n日志：{log_dir}')
    sys.excepthook = report_error
    try:
        window = Window()
    except Exception as error:
        logging.exception('启动失败')
        QMessageBox.critical(None, '启动失败', f'{error}\n请确认完整词库已打包。日志：{log_dir}')
        return 1
    window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
