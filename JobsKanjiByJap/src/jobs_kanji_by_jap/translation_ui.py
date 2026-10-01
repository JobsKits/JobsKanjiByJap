"""后台翻译与界面生命周期隔离；关闭页面后不访问已销毁控件。Created by Jobs."""
import logging
import weakref
from pathlib import Path
from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot, QStandardPaths
from shiboken6 import isValid
from .chinese import LocalChinese


class Worker(QObject):
    ready = Signal(dict)

    def __init__(self, path):
        super().__init__()
        self.path = path
        self.engine = None

    @Slot(list)
    def translate(self, sources):
        if QThread.currentThread().isInterruptionRequested():
            return
        try:
            if self.engine is None:
                self.engine = LocalChinese(self.path)
            for start in range(0, len(sources), 16):
                if QThread.currentThread().isInterruptionRequested():
                    return
                self.ready.emit(self.engine.translate(sources[start:start+16]))
        except Exception:
            logging.exception('本机中文翻译失败')
            self.ready.emit({s: '中文翻译暂不可用，请重启软件后重试' for s in sources})

    @Slot()
    def close(self):
        if self.engine:
            self.engine.close()


class ChineseLabels(QObject):
    requested = Signal(list)

    def __init__(self, parent):
        super().__init__(parent)
        path = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)) / 'chinese-v2.sqlite'
        self.reader = LocalChinese(path)
        self.pending = {}
        self.inflight = set()
        self.thread = QThread()
        self.worker = Worker(path)
        self.worker.moveToThread(self.thread)
        self.requested.connect(self.worker.translate)
        self.worker.ready.connect(self.apply)
        self.thread.finished.connect(self.worker.close)
        self.thread.finished.connect(self.worker.deleteLater)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(30)
        self.timer.timeout.connect(self.flush)
        self.thread.start()

    def bind(self, widget, sources, prefix='', suffix=''):
        sources = tuple(s for s in sources if s)
        widget.setProperty('translation_sources', sources)
        widget.setProperty('translation_prefix', prefix)
        widget.setProperty('translation_suffix', suffix)
        if not sources:
            widget.setText(prefix + '字库未收录释义')
            return
        values = [self.reader.cached(s) for s in sources]
        if all(v is not None for v in values):
            widget.setText(prefix + '；'.join(values) + suffix)
            return
        widget.setText(prefix + '正在生成中文释义…')
        for source in sources:
            self.pending.setdefault(source, []).append(weakref.ref(widget))
        self.timer.start()

    @Slot()
    def flush(self):
        work = []
        for source, refs in list(self.pending.items()):
            living = [r for r in refs if r() is not None and isValid(r())]
            if not living:
                self.pending.pop(source, None)
            elif source not in self.inflight:
                self.pending[source] = living
                work.append(source)
        if work:
            self.inflight.update(work)
            self.requested.emit(work)

    @Slot(dict)
    def apply(self, values):
        widgets = {}
        for source in values:
            self.inflight.discard(source)
            for ref in self.pending.pop(source, []):
                widget = ref()
                if widget is not None and isValid(widget):
                    widgets[id(widget)] = widget
        for widget in widgets.values():
            sources = widget.property('translation_sources')
            translated = [values.get(s) or self.reader.cached(s) for s in sources]
            if all(v is not None for v in translated):
                widget.setText(widget.property('translation_prefix') + '；'.join(translated) + widget.property('translation_suffix'))
            else:
                for source in sources:
                    if not (values.get(source) or self.reader.cached(source)):
                        self.pending.setdefault(source, []).append(weakref.ref(widget))

    def close(self):
        self.timer.stop()
        self.pending.clear()
        self.thread.requestInterruption()
        self.thread.quit()
        self.thread.wait()
        self.reader.close()
