#!/bin/zsh
# 脚本自述：JobsKanjiByJap macOS 打包入口。
# 在本工程隔离环境中补齐缺失依赖并生成 APP / DMG；不修改系统 Python。
# 运行先展示说明，回车确认；日志位于系统临时目录 JobsKanjiByJap-build.log。
# shell: zsh
# 展示无副作用的内置说明。
# 仅渲染自述：标题红色加粗，编号正文蓝色常规字重；非彩色终端输出纯文本。
jobs_intro_style() {
  local intro_color=0
  if [ -t 1 ] && [ -n "${TERM:-}" ] && [ "${TERM:-}" != dumb ] &&
     [ -z "${NO_COLOR+x}" ] && [ "${PLAIN_OUTPUT:-0}" != 1 ] &&
     [ "${IS_SOURCETREE_RUNTIME:-0}" != 1 ]; then
    intro_color=1
  fi
  /usr/bin/awk -v color="$intro_color" -v role="${1:-body}" '
    BEGIN { esc = sprintf("%c", 27) }
    {
      gsub(esc "\\[[0-9;]*m", "")
      gsub(/\\(033|e|x1[bB])\[[0-9;]*m/, "")
      if (!color || $0 ~ /^[[:space:]]*$/) { print; next }
      numbered = ($0 ~ /^[[:space:]➤ℹ🔹✔⚠]*([0-9]+[、.)）]|[0-9]+️⃣|[-•])/)
      heading = ($0 ~ /^[[:space:]]*#{1,6}[[:space:]]/ || $0 ~ /[：:][[:space:]]*$/ || $0 ~ /^[[:space:]]*[=━─-]{3}/)
      title = (!numbered && (role == "title" || heading))
      if (role == "auto" && !seen && !numbered) title = 1
      if ($0 !~ /^[[:space:]]*[=━─-]+[[:space:]]*$/) seen = 1
      printf "%s%s%s\n", esc (title ? "[1;31m" : "[0;34m"), $0, esc "[0m"
    }
  '
}
show_script_intro_and_wait() {
    print 'JobsKanjiByJap · macOS 打包' | jobs_intro_style body
    print '将进入工程，检查 Python、隔离环境、Qt 和 PyInstaller；缺依赖时回车安装，任意字符取消。' | jobs_intro_style body
    print '产物：同目录 dist/YYYY.MM.DD HH-mm-ss；日志：系统临时目录 JobsKanjiByJap-build.log。' | jobs_intro_style body
    print '按回车继续，Ctrl+C 取消。会清理旧 dist；成功后打开产物目录并启动软件。' | jobs_intro_style body
    [[ -t 0 ]] || { print '请在终端中交互运行。'; exit 1; }
    print '构建产物按本机年月日时分秒保存到 dist/YYYY.MM.DD HH-mm-ss/（例如 2020.06.04 12-23-21），同次构建共用一个时间目录。' | jobs_intro_style body
    print '打包前清理旧 dist；成功后在第一层更新产物快捷方式、打开目录并启动本机软件。' | jobs_intro_style body
    read -r '?确认：' _
}
# 检查当前系统及实际可运行的 Python。
check_environment() {
    setopt NO_NOMATCH
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-${(%):-%x}}")" && pwd)"
    [[ "$(uname -s)" == 'Darwin' ]] || { print '仅支持 macOS。'; exit 1; }
    command -v python3 >/dev/null || { print '请先安装 Python 3.11–3.14。'; exit 1; }
    python3 -c 'import sys,venv; assert (3,11)<=sys.version_info<(3,15)' || { print 'Python 环境不可用。'; exit 1; }
}
# 交由 Python 构建入口记录完整日志并传播失败。
run_business() {
    python3 "$SCRIPT_DIR/JobsKanjiByJap/scripts/bootstrap.py" build
    local result=$?
    [[ $result == 0 ]] && print '✔ 构建成功' || print '✖ 构建失败，请检查日志。'
    exit $result
}
# 编排自述、检查和构建。
main() {
    show_script_intro_and_wait # 双击后先确认影响范围。
    check_environment # 校验当前工具链。
    run_business # 构建并保留日志。
}
main "$@"
