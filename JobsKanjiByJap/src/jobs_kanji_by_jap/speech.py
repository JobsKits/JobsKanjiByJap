"""系统日语语音；新点读中断旧点读，缺语音时明确提示。Created by Jobs."""
import sys
from PySide6.QtCore import QObject, Signal, QLocale
from PySide6.QtTextToSpeech import QTextToSpeech


class Speech(QObject):
    message = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        engines = [e for e in QTextToSpeech.availableEngines() if e != 'mock']
        preferred = 'darwin' if sys.platform == 'darwin' else 'sapi'
        backend = preferred if preferred in engines else (engines[0] if engines else '')
        self.engine = QTextToSpeech(backend, self) if backend else QTextToSpeech(self)
        self.engine.errorOccurred.connect(lambda *_: self.message.emit('发音失败：' + self.engine.errorString()))
        self.voices = []
        for locale in self.engine.availableLocales() if engines else []:
            if locale.language() == QLocale.Language.Japanese:
                self.engine.setLocale(locale)
                self.voices.extend(v for v in self.engine.availableVoices() if v not in self.voices)
        if self.voices:
            self.engine.setVoice(self.voices[0])
        self.engine.setRate(-0.15)

    def say(self, text):
        if not self.voices:
            self.message.emit('没有可用日语语音：请在 macOS 辅助功能→朗读内容，或 Windows 语言与语音设置中安装日语语音，然后重启软件。')
            return False
        self.engine.stop()
        self.engine.say(text)
        self.message.emit('正在朗读：' + text)
        return True

    def set_voice(self, index):
        if 0 <= index < len(self.voices):
            self.engine.stop()
            self.engine.setVoice(self.voices[index])
