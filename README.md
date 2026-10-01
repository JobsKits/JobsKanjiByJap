# JobsKanjiByJap · 日语汉字点读

![Jobs出品，必属精品](https://picsum.photos/1500/400)

[toc]

---

[▶ 观看日语汉字点读演示视频](./showMeNow.mp4)

https://github.com/user-attachments/assets/34c38e1e-97f2-4e26-8e25-eb6fdcb8ee82

## 🔥 <font id=前言>前言</font>

用 [**Python**](https://www.python.org) 和 [**PySide6**](https://doc.qt.io/qtforpython-6/) 编写的离线桌面学习工具。查汉字、看音读 / 训读 / 名乘、按具体词语查中文词性和释义、点击假名发音。学习内容只显示中文与日文。右上角“主题”可选择日间、夜间或跟随系统，即时生效并记住选择。首次默认日间；日间使用暖白背景和深色正文，夜间使用深灰背景和浅色正文；跟随系统会响应系统外观变化。滚动区、弹窗、下拉菜单和红色振假名同步适配。例句的振假名以红色显示在对应汉字上方，熟字训按词整体标注。

读音不由词性单独决定。例如「生きる＝いきる」「学生＝がくせい」「生ビール＝なまビール」。自动词 / 他动词、送假名、连浊和熟字训也需要结合词语学习。

## 一、功能与覆盖范围

| 内容 | 当前收录 |
| --- | ---: |
| KANJIDIC2 汉字 | 13,108 |
| JMdict 词条 | 218,844 |
| 有例句的词条 | 28,929 |
| 不同日语例句 | 26,269 |
| 原字库无读音的字 | 751 |
| 原字库无英文释义的字 | 2,724 |
| 未匹配到 JMdict 词条的字 | 7,092 |
| 在 JMdict 中有例句关联的字 | 3,820 |
| 中文学习示例 | 12 个字、38 个示例 |

**当前不能宣称覆盖日语历史上所有汉字、人名读法、异体字和每个读音的例句。** 全量指导入了本次 KANJIDIC2 文件的全部条目；常用字、扩展字、生僻字数据质量有差异。未收录的字段明确显示缺项。

- 保留原词典的音读、训读、名乘、读法适用写法、义项适用读法及原始标记。
- 字义、词义、用法和例句译文显示中文，不显示英文原解释。已为全部 13,108 个汉字建立中文显示记录，其中 9,271 条可显示中文辅助译文，1,113 条显示“中文译文待校对”，2,724 条原库缺释义；词义与例句译文由随包离线模型按需生成并缓存，首次查看短暂显示“正在生成中文释义”。机器翻译明确标注，未通过全量人工校对；失败显示中文提示，不以英文兜底。
- `生、日、行、上、下、人、月、大、食、見、読、水` 另附中文学习讲解。所有词性使用固定中文映射，例如“一段动词／他动词”。中文检索反查已收录的中文字义；本工具是中日对照词典，不是任意长文翻译器。
- 常见多音字学习卡使用明确指定的红色振假名。其他例句使用 [**Sudachi**](https://github.com/WorksApplications/sudachi.rs) 分词结果，可能存在同形词歧义；2 条句子含未识别读音，界面明确显示“未识别”。
- 例句从词义层级关联；一个词义的例句不代表适用于该词所有读法。点击 Tatoeba 原句链接可查看作者及校对信息。
- 发音使用系统日语合成语音。点击假名时按假名朗读，新的点读会停止上一次朗读。不承诺音调词典级重音准确性。

## 二、使用方式

1、打开打包后的 `JobsKanjiByJap.app`，或 Windows 分发目录内的 `JobsKanjiByJap.exe`。

2、左侧输入汉字、日语词语、假名或中文字义。选择“全部收录汉字 / 常用汉字 / 人名用汉字”。

3、选择汉字，右侧点击音读、训读、名乘或中文学习卡的读音按钮。

4、词语区域点击“词义 / 例句”，查看这个写法和读法对应的词义。点击红字振假名句子可点读。

5、左下方调整日语语音、语速，或点击停止。

中文讲解、词库、例句和离线翻译模型均随软件携带；打开原句来源链接、安装依赖、主动更新词库需要联网。

## 三、源码与目录

```text
JobsKanjiByJap.py/
├── README.md
├── showMeNow.mp4                 # 软件演示视频
├── 【MacOS】📦生成dmg.command
├── 【Windows】📦生成exe.bat
├── dist/                         # 每次构建先清理旧产物
└── JobsKanjiByJap/
    ├── pyproject.toml
    ├── src/jobs_kanji_by_jap/            # UI、语音、查询、振假名及 assets 词库
    ├── scripts/                  # 运行、构建、依赖检查、更新语料
    ├── tests/
    └── work/                     # 构建缓存及下载，不属于源码
```

源码运行（从外层目录）：

```shell
python3 JobsKanjiByJap/scripts/bootstrap.py run
```

Windows 对应使用 `py -3 JobsKanjiByJap/scripts/bootstrap.py run`。入口先显示内置说明并等待确认；环境缺依赖时直接回车安装，输入任意字符后回车取消整个流程。依赖放入工程 `.venv`，不升级系统 Python。已有 `.venv` 损坏时停止，并提示先改名备份。

## 四、双平台打包

依赖链：Python 3.11–3.14 → venv / pip → PySide6 / PyInstaller / CTranslate2 / SentencePiece → 应用、词库与离线模型；macOS 生成 DMG 还依赖系统 `hdiutil` 和 `ditto`。正常打包使用已附词库，不安装分词器或重新下载语料。

| 入口 | 运行平台 | 输出 | 环境检查 |
| --- | --- | --- | --- |
| `./【MacOS】📦生成dmg.command` | macOS 14 或更高 | APP + 当前架构 DMG | zsh、Python、隔离环境、依赖、hdiutil |
| `./【Windows】📦生成exe.bat` | Windows 10 / 11 | EXE 文件夹 + ZIP | Python Launcher 或 python、隔离环境、依赖 |

[**PyInstaller**](https://pyinstaller.org/en/stable/operating-mode.html) 必须在目标系统打包：macOS 不能直接生成可验证的 Windows EXE。Apple Silicon 与 Intel 请分别在相应架构环境构建；当前 macOS 产物为 arm64。Windows 分发必须保留整个 `JobsKanjiByJap` 文件夹，不能只复制 EXE。

双击入口会先确认，再调用 Python 入口确认；只有缺少依赖时才询问联网安装，不主动升级已有环境。构建产物包含 Python 运行时、Qt、词库和离线模型，终端用户不需要安装 Python。日语语音由目标系统提供。

此工程不含 Apple Developer ID 签名、公证或 Windows 商业签名。公共发行需要发行者自行签名，并保留词典及第三方许可。

## 五、数据来源、更新与日志

词典来自 [**EDRDG**](https://www.edrdg.org/edrdg/licence.html)，字库和派生 SQLite 数据采用 CC BY-SA 4.0。例句来自 [**Tatoeba**](https://tatoeba.org/en/terms_of_use)，保留句子来源 ID 和原句链接。原始来源地址、SHA-256、构建时间见 `./JobsKanjiByJap/src/jobs_kanji_by_jap/assets/coverage.json`；完整归属见同目录 `NOTICE.txt`，打包时会收集 Qt 等依赖许可。中文转换使用 [**Argos 模型**](https://github.com/argosopentech/argospm-index) 和 [**CTranslate2**](https://opennmt.net/CTranslate2/) 本地推理；模型包说明采用 CC BY 4.0，模型作者为 Jörg Tiedemann 和 Santhosh Thottingal，模型原始说明及文件随源码保留。

主动更新（关闭应用后执行）：

```shell
python3 JobsKanjiByJap/scripts/bootstrap.py update
```

更新动作直接回车跳过，输入任意字符执行。必要时安装 `corpus` 依赖，从官方站点下载，校验 gzip 并重建临时数据库，完整性检查通过后替换词库。失败不替换已完成数据库。随后按需重建中文字义缓存，再重新打包。不要同时运行多个词库构建进程。

构建与运行启动日志：系统临时目录 `JobsKanjiByJap-build.log`、`JobsKanjiByJap-run.log`、`JobsKanjiByJap-update.log`。中文缓存：系统应用数据目录中的 `chinese-v2.sqlite`，只保存公开词典的中文转换结果。学习期间不调用在线翻译服务、不需要密钥。应用异常日志：系统应用数据目录 `Jobs/JobsKanjiByJap/logs/app.log`（具体目录由 Qt 按系统决定，报错弹窗给出路径）。

### Git 克隆后的资源准备

Git 仓库不包含大型 `catalog.sqlite` 词库、`model.bin` 模型权重、虚拟环境和构建产物；本地已有资源不受忽略规则影响。完整安装包仍包含运行所需资源。仅克隆源码后，须先准备以下资源，再运行或打包：

1、从 `./JobsKanjiByJap/src/jobs_kanji_by_jap/assets/translation_manifest.json` 记录的地址下载 Argos 模型包，并核对该文件记录的 SHA-256。模型包为 ZIP 格式，将包内 `model/model.bin` 放入 `./JobsKanjiByJap/src/jobs_kanji_by_jap/assets/translation/en_zh/model/model.bin`；保留仓库已有的模型配置和许可证。

2、在仓库根目录运行 `python3 JobsKanjiByJap/scripts/bootstrap.py update`，按提示确认安装缺失依赖并重建词库及中文缓存。此步骤需要联网并耗费较长时间；准备完成后再执行平台打包入口。

添加源码使用 `git add .`，让 Git 自己遵守忽略规则；不要用 `git add *` 将被忽略目录作为显式参数传入，也不要强制添加词库、模型或安装包。

## 六、验证与限制

提供 `unittest` 检查词库完整性、关键多音字、词义限制、振假名送假名保留、检索和分页；Qt 离屏检查验证界面构造及截图。最终执行记录见 `./验证结果.txt`。

Windows 入口已静态审查，未在 Windows 真机执行。学习界面已停止显示英文解释，但 1,113 条预制字义仍需中文校对，机器译文未全量人工核对；缺失读音、无源释义、生僻字逐音例句尚未补齐；这些是语料缺口，不能用自动拼接读音或自动造句冒充字典事实。

## 七、常见问题

**没有声音？** 安装系统日语语音。macOS：系统设置 → 辅助功能 → 朗读内容 / 朗读与语音 → 系统声音；Windows：设置 → 时间和语言 → 语言 / 语音。安装后重启应用，软件会重新枚举日语语音。系统语音引擎不可用时状态栏会明确报错。

**为什么训读有点号？** 例如「い.きる」中的点号用于区分汉字对应部分和送假名；播放时去掉点号，读作「いきる」。

**为什么汉字没有例句？** 字库比现代通用词库范围更大。没有语料就展示缺项；不从某个读音自动编造用法。

**中文解释需要联网吗？** 不需要。离线模型随软件提供，后台翻译不阻塞窗口；译文持久缓存，下次直接显示。原始词典仍留在内部以便追溯义项，学习界面只展示中文与日文。

**机器译文是否等于权威日汉词典？** 不等于。多义词和短释义可能产生歧义，按页面“机器翻译”标记辨别；12 个重点字另有原创中文学习卡，其他内容尚未逐条人工审校。

打包前会清理该应用工程的旧 `dist` 产物，清理失败则停止；成功后自动打开当前平台产物的磁盘位置并运行本次生成的 APP / EXE，结尾无需回车。失败时不启动软件；运行前的防误触确认保留。

必需依赖缺失时，直接回车联网安装；输入任意字符后回车取消整个流程。安装失败或复检仍不可用时停止，不继续清理旧产物或打包。健康依赖直接复用；可选升级和词库更新仍为回车跳过、任意字符执行。

第一层交付目录与平台打包脚本同层保存 `dist/`，以及最新 APP / DMG 的相对符号链接（Mac）或 EXE / 分发包的 `.lnk`（Windows）。双击快捷方式即可接触成品，真实文件保留在 `dist/`；成功构建自动更新入口，清理旧产物时移除对应旧入口。尚无成品时不生成无效快捷方式。

构建产物使用本机本地构建时间，格式为 `YYYY.MM.DD HH-mm-ss`（年月日时分秒），例如 `2020.06.04 12-23-21`。每次构建的 APP、DMG、EXE、ZIP 和配套文件统一保存到交付层 `./dist/YYYY.MM.DD HH-mm-ss/`，同次构建只取一次时间；第一层快捷方式指向本次时间目录，成功后打开该目录并启动其中的软件。旧产物沿用原有清理规则；历史产物缺少可靠构建时间时，不补写推测时间。

<a id="🔚" href="#前言" style="font-size:17px; color:green; font-weight:bold;">我是有底线的➤点我回到首页</a>
