"""全局阅读主题及偏好持久化。Created by Jobs."""
from PySide6.QtCore import QObject, QSettings, Qt
from PySide6.QtGui import QColor, QPalette

DARK_COLORS = {
    '#f5f3ee': '#20272c', '#223945': '#e7eef1',
    '#184e59': '#99dce0', '#607680': '#b0c1c9',
    '#fff2d7': '#40392a', '#675331': '#f4dbaa',
    '#fff': '#2b353c', 'white': '#2b353c', '#ffffff': '#2b353c',
    '#c9d8d9': '#596c76', '#e3f0ef': '#374b53', '#427e82': '#83cbd0',
    '#9babb0': '#83969e', '#dde3df': '#4b5d67', '#286772': '#386f7b',
    '#fff8e9': '#383e40', '#ecebe5': '#252e34', '#adbdbb': '#758a95',
    '#e8edeb': '#263239', '#eef3f0': '#313f47', '#647982': '#afbec6',
    '#186875': '#9adae6', '#536380': '#c1b9e8', '#71847e': '#617881',
    '#536761': '#162026',
}

STYLE = '''
QWidget {font-size:14px;color:#223945;}
QMainWindow, QDialog {background:#f5f3ee;}
QLabel#brand {font-size:25px;font-weight:700;color:#184e59;}
QLabel#kanji {font-size:72px;font-weight:600;}
QLabel#heading {font-size:21px;font-weight:650;}
QLabel#muted {color:#607680;}
QLabel#notice {background:#fff2d7;padding:12px;border-radius:8px;color:#675331;}
QPushButton {background:#fff;border:1px solid #c9d8d9;border-radius:7px;padding:8px 12px;}
QPushButton:hover {background:#e3f0ef;border-color:#427e82;}
QPushButton:focus {border:2px solid #427e82;}
QPushButton:disabled {color:#9babb0;}
QLineEdit,QComboBox {background:white;border:1px solid #c9d8d9;border-radius:6px;padding:9px;}
QListWidget {background:white;border:1px solid #dde3df;border-radius:8px;font-size:19px;}
QListWidget::item {padding:9px;}
QListWidget::item:selected {background:#286772;color:#faffff;}
QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget {border:none;background:#f5f3ee;}
QTextBrowser {background:#ffffff;color:#223945;border:1px solid #c9d8d9;}
QComboBox QAbstractItemView {background:#ffffff;color:#223945;selection-background-color:#286772;selection-color:#faffff;}
QToolTip {background:#fff8e9;color:#223945;border:1px solid #c9d8d9;}
QScrollBar:vertical {background:#ecebe5;width:12px;border:none;}
QScrollBar::handle:vertical {background:#adbdbb;min-height:28px;border-radius:6px;}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {height:0;}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {background:none;}
QWidget#card {background:white;border:1px solid #dde3df;border-radius:10px;}
QStatusBar {background:#e8edeb;}
'''


def apply_theme(app, dark=False):
    palette = QPalette()
    colors = {
        QPalette.ColorRole.Window: '#f5f3ee',
        QPalette.ColorRole.WindowText: '#223945',
        QPalette.ColorRole.Base: '#ffffff',
        QPalette.ColorRole.AlternateBase: '#eef3f0',
        QPalette.ColorRole.Text: '#223945',
        QPalette.ColorRole.Button: '#ffffff',
        QPalette.ColorRole.ButtonText: '#223945',
        QPalette.ColorRole.ToolTipBase: '#fff8e9',
        QPalette.ColorRole.ToolTipText: '#223945',
        QPalette.ColorRole.Highlight: '#286772',
        QPalette.ColorRole.HighlightedText: '#faffff',
        QPalette.ColorRole.PlaceholderText: '#647982',
        QPalette.ColorRole.Link: '#186875',
        QPalette.ColorRole.LinkVisited: '#536380',
        QPalette.ColorRole.Light: '#ffffff',
        QPalette.ColorRole.Midlight: '#e8edeb',
        QPalette.ColorRole.Mid: '#adbdbb',
        QPalette.ColorRole.Dark: '#71847e',
        QPalette.ColorRole.Shadow: '#536761',
    }
    for role, color in colors.items():
        palette.setColor(QPalette.ColorGroup.All, role, QColor(DARK_COLORS.get(color, color) if dark else color))
    app.setPalette(palette)
    style = STYLE
    if dark:
        import re
        style = re.sub(r'#[0-9a-fA-F]{6}|#fff\b|\bwhite\b',
                       lambda match: DARK_COLORS.get(match.group(), match.group()), style)
    app.setProperty('rubyColor', '#ff8792' if dark else '#c52e38')
    app.setStyleSheet(style)
    for widget in app.allWidgets():
        widget.update()


class ReadingTheme(QObject):
    """跟随系统时释放 Qt 配色覆盖，并监听系统主题变化。"""
    def __init__(self, app, settings=None):
        super().__init__(app)
        self.app = app
        self.settings = settings if settings is not None else QSettings('Jobs', 'JobsKanjiByJap')
        self.mode = self.settings.value('appearance/theme', 'light')
        self._changing = False
        app.styleHints().colorSchemeChanged.connect(self.system_changed)
        self.set_mode(self.mode)

    def set_mode(self, mode):
        self.mode = mode if mode in ('light', 'dark', 'system') else 'light'
        self.settings.setValue('appearance/theme', self.mode)
        self.settings.sync()
        self._changing = True
        try:
            hints = self.app.styleHints()
            if self.mode == 'system':
                hints.unsetColorScheme()
            else:
                hints.setColorScheme(Qt.ColorScheme.Dark if self.mode == 'dark' else Qt.ColorScheme.Light)
        finally:
            self._changing = False
        self.system_changed(self.app.styleHints().colorScheme())

    def system_changed(self, scheme):
        if self._changing:
            return
        dark = self.mode == 'dark' or (self.mode == 'system' and scheme == Qt.ColorScheme.Dark)
        apply_theme(self.app, dark)
