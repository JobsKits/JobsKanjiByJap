"""检查隔离环境，缺失时安装声明依赖，然后运行或打包。Created by Jobs."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import venv

ROOT = Path(__file__).resolve().parents[1]


def source_environment():
    """从当前工程加载源码，兼容目录迁移和重命名。"""
    environment = os.environ.copy()
    environment['PYTHONPATH'] = os.pathsep.join(filter(None, [str(ROOT / 'src'), environment.get('PYTHONPATH')]))
    return environment


def call(args, log_path):
    with log_path.open('a', encoding='utf-8') as log:
        log.write('执行：' + repr(args) + '\n')
        with subprocess.Popen(args, cwd=ROOT, env=source_environment(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, encoding='utf-8', errors='replace') as process:
            for line in process.stdout:
                print(line, end='', flush=True)
                log.write(line)
            result = process.wait()
    if result:
        raise SystemExit(f'执行失败 ({result})；日志：{log_path}')


def confirm_required_install(message):
    """缺失必需依赖时回车安装，任何非空输入取消整个流程。"""
    try:
        answer = input(message + "：直接回车安装，输入任意字符后回车取消：")
    except EOFError:
        raise SystemExit("没有交互输入，已取消依赖安装。")
    if answer != "":
        raise SystemExit("已取消依赖安装，停止当前流程。")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['run', 'build', 'update'])
    args = parser.parse_args()
    if not (3, 11) <= sys.version_info < (3, 15):
        raise SystemExit('需要 Python 3.11–3.14。')
    log = Path(tempfile.gettempdir()) / ('JobsKanjiByJap-' + args.action + '.log')
    print(f'JobsKanjiByJap：{args.action}。仅操作此工程的 .venv、词库及 dist。日志：{log}')
    print('运行与打包按回车继续，Ctrl+C 取消。更新词库时直接回车跳过。')
    answer = input('> ')
    if args.action == 'update' and not answer.strip():
        raise SystemExit('已跳过词库更新。')
    env = ROOT / '.venv'
    python = env / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
    if not python.exists():
        venv.EnvBuilder(with_pip=True).create(env)
    health = subprocess.run([str(python), '-c', 'import sys,pip; assert (3,11)<=sys.version_info<(3,15)'], capture_output=True)
    if health.returncode:
        raise SystemExit('工程 .venv 损坏或版本不兼容，请改名备份后重试。')
    modules = ['PySide6.QtWidgets', 'PySide6.QtTextToSpeech', 'jobs_kanji_by_jap', 'ctranslate2', 'sentencepiece']
    modules += ['PyInstaller'] if args.action == 'build' else []
    modules += ['sudachipy', 'sudachidict_core'] if args.action == 'update' else []
    probe = ';'.join('import ' + name for name in modules)
    if subprocess.run([str(python), '-c', probe], cwd=ROOT, env=source_environment(), capture_output=True).returncode:
        confirm_required_install('需要联网补齐工程依赖')
        extra = {'build': '[build]', 'update': '[corpus]', 'run': ''}[args.action]
        call([str(python), '-m', 'pip', 'install', '-e', str(ROOT) + extra], log)
        call([str(python), '-c', probe], log)
    command = {'run': ['-m', 'jobs_kanji_by_jap.app'], 'build': [str(ROOT / 'scripts/build.py')],
               'update': [str(ROOT / 'scripts/build_catalog.py'), '--refresh']}[args.action]
    call([str(python)] + command, log)
    if args.action == 'update':
        call([str(python), str(ROOT / 'scripts/prepare_chinese.py')], log)


if __name__ == '__main__':
    main()
