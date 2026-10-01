@echo off
chcp 65001 >nul
setlocal
rem JobsKanjiByJap Windows build: isolated venv, bundled runtime, timestamped output.
echo JobsKanjiByJap Windows 打包：生成自带 Python 和离线词库的 EXE 文件夹及 ZIP。
echo 影响范围：当前工程 .venv、work 和 dist。缺少依赖时直接回车联网安装，输入任意字符取消。
echo 日志：系统临时目录 JobsKanjiByJap-build.log。按任意键继续，Ctrl+C 取消。
echo Output: dist\YYYY.MM.DD HH-mm-ss\ using local build time, shared by all artifacts.
echo Build clears old dist. On success, reveal output and launch the packaged app.
pause >nul
where py >nul 2>nul
if errorlevel 1 goto use_python
py -3 "%~dp0JobsKanjiByJap\scripts\bootstrap.py" build
goto finished
:use_python
where python >nul 2>nul
if errorlevel 1 goto no_python
python "%~dp0JobsKanjiByJap\scripts\bootstrap.py" build
goto finished
:no_python
echo 请安装 Python 3.11-3.14 并启用 PATH，然后重新运行。
pause
exit /b 1
:finished
set "JOBS_RESULT=%ERRORLEVEL%"
if not "%JOBS_RESULT%"=="0" echo 构建失败，请查看日志。
exit /b %JOBS_RESULT%
