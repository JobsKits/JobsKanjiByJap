"""在当前系统生成独立运行的应用；不交叉编译。Created by Jobs."""
from datetime import datetime
import importlib.metadata
from artifact_shortcuts import clear_shortcuts, publish_shortcuts
from pathlib import Path
import platform
import shutil
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    if sys.platform not in ['darwin', 'win32']:
        raise SystemExit('仅支持在 macOS / Windows 本机打包。')
    if sys.platform == 'darwin' and not shutil.which('hdiutil'):
        raise SystemExit('缺少系统 hdiutil，无法创建 DMG。')
    assets = ROOT / 'src/jobs_kanji_by_jap/assets'
    if not (assets / 'catalog.sqlite').is_file():
        raise SystemExit('缺少词库，请先运行 bootstrap.py update。')
    required = ['chinese_seed.sqlite', 'translation/en_zh/model/model.bin', 'translation/en_zh/sentencepiece.model']
    for name in required:
        if not (assets / name).is_file():
            raise SystemExit('缺少离线中文资源：' + name)
    with sqlite3.connect(assets / 'chinese_seed.sqlite') as seed:
        with sqlite3.connect(assets / 'catalog.sqlite') as catalog:
            if seed.execute('SELECT count(*) FROM kanji_zh').fetchone()[0] != catalog.execute('SELECT count(*) FROM kanji').fetchone()[0]:
                raise SystemExit('中文字义尚未准备完成，请先运行 scripts/prepare_chinese.py。')
    stamp = datetime.now().strftime('%Y.%m.%d %H-%M-%S')
    dist_root = ROOT.parent / "dist"
    if dist_root.is_symlink():
        raise SystemExit("拒绝清理符号链接 dist，请检查输出目录。")
    clear_shortcuts(ROOT.parent)
    if dist_root.exists():
        shutil.rmtree(dist_root)
    output = ROOT.parent / 'dist' / stamp
    output.mkdir(parents=True, exist_ok=False)
    licenses = ROOT / 'work' / stamp / 'licenses'
    licenses.mkdir(parents=True)
    manifests = []
    for name in ['PySide6', 'PySide6_Essentials', 'PySide6_Addons', 'shiboken6', 'pyinstaller', 'ctranslate2', 'sentencepiece', 'numpy', 'pyyaml']:
        dist = importlib.metadata.distribution(name)
        manifests.append(f'{name} {dist.version}\n{dist.metadata.get("License", "See included license files")}')
        for item in dist.files or []:
            if any(part.lower() in ['licenses', 'license', 'license.txt', 'copying'] for part in item.parts):
                path = Path(dist.locate_file(item))
                if path.is_file():
                    target = licenses / name / str(item)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, target)
    (assets / 'THIRD_PARTY.txt').write_text('\n\n'.join(manifests), encoding='utf-8')
    args = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--windowed', '--name', 'JobsKanjiByJap',
            '--distpath', str(output), '--workpath', str(ROOT / 'work' / stamp / 'pyinstaller'),
            '--specpath', str(ROOT / 'work' / stamp), '--paths', str(ROOT / 'src'),
            '--collect-data', 'jobs_kanji_by_jap', '--add-data', f'{licenses}{":" if sys.platform == "darwin" else ";"}licenses',
            '--collect-all', 'ctranslate2', '--collect-all', 'sentencepiece', '--exclude-module', 'torch', '--exclude-module', 'transformers', '--exclude-module', 'sudachipy', '--exclude-module', 'sudachidict_core']
    if sys.platform == 'darwin':
        args += ['--osx-bundle-identifier', 'com.jobs.kanjibyjap']
    args.append(str(ROOT / 'scripts/launch.py'))
    subprocess.run(args, check=True, cwd=ROOT)
    shutil.copy2(ROOT.parent / 'README.md', output / 'README.md')
    if sys.platform == 'darwin':
        stage = ROOT / 'work' / stamp / 'dmg'
        stage.mkdir()
        subprocess.run(['ditto', str(output / 'JobsKanjiByJap.app'), str(stage / 'JobsKanjiByJap.app')], check=True)
        (stage / 'Applications').symlink_to('/Applications')
        shutil.copy2(ROOT.parent / 'README.md', stage / 'README.md')
        subprocess.run(['hdiutil', 'create', '-volname', 'JobsKanjiByJap', '-srcfolder', str(stage), '-format', 'UDZO',
                        str(output / f'JobsKanjiByJap-macOS-{platform.machine()}.dmg')], check=True)
    else:
        shutil.make_archive(str(output / ('JobsKanjiByJap-Windows-' + platform.machine())), 'zip', output, 'JobsKanjiByJap')
    print('打包完成：', output)
    artifact = output / "JobsKanjiByJap.app" if sys.platform == "darwin" else output / "JobsKanjiByJap" / "JobsKanjiByJap.exe"
    if not artifact.exists():
        raise SystemExit("构建产物不存在：" + str(artifact))
    packages = sorted(output.glob("*.dmg" if sys.platform == "darwin" else "*.zip"))
    publish_shortcuts(ROOT.parent, [artifact, *packages])
    if sys.platform == "darwin":
        subprocess.run(["open", str(output)], check=True)
        subprocess.run(["open", str(output / "JobsKanjiByJap.app")], check=True)
    else:
        subprocess.run(["explorer.exe", str(output)], check=False)
        subprocess.Popen([str(output / "JobsKanjiByJap" / "JobsKanjiByJap.exe")], cwd=output)



if __name__ == '__main__':
    main()
