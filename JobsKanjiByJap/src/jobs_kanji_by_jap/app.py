"""JobsKanjiByJap 原生双平台学习界面。Created by Jobs."""
# JOBS_TERMINAL_STYLE_GUARD_V1_BEGIN
# 保存与恢复由监督进程负责；导入本模块时不接管终端。
def _jobs_terminal_style_bootstrap_v1():
    import os as _os
    import base64 as _base64
    import json as _json
    import shutil as _shutil
    import subprocess as _subprocess
    import sys as _sys
    import tempfile as _tempfile

    _entry = _os.path.abspath(__file__)
    if _os.environ.get("JOBS_TERMINAL_STYLE_REEXEC") == _entry:
        _os.environ.pop("JOBS_TERMINAL_STYLE_REEXEC", None)
        return
    if (getattr(_sys, "frozen", False) or not _sys.stdin or not _sys.stdout
            or not _sys.stdin.isatty() or not _sys.stdout.isatty()
            or "NO_COLOR" in _os.environ
            or _os.environ.get("PLAIN_OUTPUT") == "1"
            or _os.environ.get("IS_SOURCETREE_RUNTIME") == "1"
            or any(_key.upper().startswith(("SOURCETREE", "SOURCE_TREE"))
                   for _key in _os.environ)):
        return
    if _os.name != "nt" and (_os.environ.get("TERM", "") in ("", "dumb")
                             or _os.environ.get("TMUX") or _os.environ.get("STY")):
        return
    _original = getattr(_sys, "orig_argv", None)
    _module_start = False
    for _argument in list(_original[1:]) if _original else []:
        if _argument == "--" or _os.path.abspath(_argument) == _entry:
            break
        if _argument in ("-c", "-m"):
            _module_start = True
            break
    if _module_start:
        _os.environ.update(NO_COLOR="1", PLAIN_OUTPUT="1", FORCE_COLOR="0", CLICOLOR="0")
        return
    _command = [_sys.executable] + (list(_original[1:]) if _original else list(_sys.argv))
    _environment = _os.environ.copy()
    _environment["JOBS_TERMINAL_STYLE_REEXEC"] = _entry
    _shell_core = r"""# 临时保护当前终端配色，业务进程自行管理原有退出清理。
jobs_terminal_style_run() {
    # 无法可靠保存原色时，沿用脚本已有的纯文本约定。
    jobs_terminal_style_plain() {
        PLAIN_OUTPUT=1
        NO_COLOR=1
        FORCE_COLOR=0
        CLICOLOR=0
        ANSI_COLORS_DISABLED=1
        npm_config_color=false
        export PLAIN_OUTPUT NO_COLOR FORCE_COLOR CLICOLOR ANSI_COLORS_DISABLED npm_config_color
        if "$@"; then
            jobs_style_exit_status=0
        else
            jobs_style_exit_status=$?
        fi
        exit "$jobs_style_exit_status"
    }
    if [ ! -t 0 ] || [ ! -t 1 ] || [ -z "${TERM:-}" ] ||
       [ "${TERM:-}" = dumb ] || [ "${NO_COLOR+x}" = x ] ||
       [ "${PLAIN_OUTPUT:-0}" = 1 ] || [ "${IS_SOURCETREE_RUNTIME:-0}" = 1 ] ||
       env | LC_ALL=C grep -qiE '^(SOURCETREE|SOURCE_TREE)'; then
        if "$@"; then
            jobs_style_exit_status=0
        else
            jobs_style_exit_status=$?
        fi
        exit "$jobs_style_exit_status"
    fi
    if [ -n "${TMUX:-}${STY:-}" ]; then
        jobs_terminal_style_plain "$@"
    fi
    jobs_style_tty=$(tty 2>/dev/null) || jobs_terminal_style_plain "$@"
    if ! ps -o pgid= -o tpgid= -p "$$" 2>/dev/null |
         LC_ALL=C awk 'NF == 2 && $1 == $2 && $1 > 0 { foreground = 1 } END { exit !foreground }'; then
        jobs_terminal_style_plain "$@"
    fi
    case ${JOBS_TERMINAL_STYLE_OWNER:-} in
        ''|*[!0-9]*) ;;
        *)
            if [ "${JOBS_TERMINAL_STYLE_TTY:-}" = "$jobs_style_tty" ] &&
               kill -0 "$JOBS_TERMINAL_STYLE_OWNER" 2>/dev/null; then
                if "$@"; then
                    jobs_style_exit_status=0
                else
                    jobs_style_exit_status=$?
                fi
                exit "$jobs_style_exit_status"
            fi
            ;;
    esac
    jobs_style_stty=$(stty -g 2>/dev/null < /dev/tty) || jobs_terminal_style_plain "$@"
    jobs_style_saved=''
    jobs_style_saved_rows=''
    jobs_style_applied_rows=''
    jobs_style_changed=0
    jobs_style_applied_complete=0
    jobs_style_query_active=0
    jobs_style_recovery=''
    jobs_style_exit_status=0
    jobs_style_esc=$(printf '\033')
    jobs_style_bel=$(printf '\007')
    # 只接受本次请求对应的 RGB 响应；非协议输入使本次探测失败。
    jobs_terminal_style_query() {
        jobs_style_query_key=$1
        printf '\033]%s;?\007' "$jobs_style_query_key" > /dev/tty || return 1
        jobs_style_reply=''
        for jobs_style_attempt in 1 2 3; do
            jobs_style_piece=$(dd bs=256 count=1 2>/dev/null < /dev/tty)
            jobs_style_reply=$jobs_style_reply$jobs_style_piece
            case $jobs_style_reply in
                *"$jobs_style_bel"|*"$jobs_style_esc\\") break ;;
                '') ;;
                "$jobs_style_esc"*) ;;
                *) break ;;
            esac
        done
        case $jobs_style_reply in
            "$jobs_style_esc]$jobs_style_query_key;rgb:"*"$jobs_style_bel")
                jobs_style_rgb=${jobs_style_reply#"$jobs_style_esc]$jobs_style_query_key;rgb:"}
                jobs_style_rgb=${jobs_style_rgb%"$jobs_style_bel"}
                ;;
            "$jobs_style_esc]$jobs_style_query_key;rgb:"*"$jobs_style_esc\\")
                jobs_style_rgb=${jobs_style_reply#"$jobs_style_esc]$jobs_style_query_key;rgb:"}
                jobs_style_rgb=${jobs_style_rgb%"$jobs_style_esc\\"}
                ;;
            *) return 1 ;;
        esac
        jobs_style_normalized=$(printf '%s\n' "$jobs_style_rgb" | LC_ALL=C awk -F/ '
            NF != 3 { exit 1 }
            {
                for (i = 1; i <= 3; i++) {
                    h = tolower($i)
                    if (length(h) < 1 || length(h) > 4 || h ~ /[^0-9a-f]/) exit 1
                    n = 0
                    for (j = 1; j <= length(h); j++) n = n * 16 + index("0123456789abcdef", substr(h, j, 1)) - 1
                    value[i] = int(n * 65535 / (16 ^ length(h) - 1) + 0.5)
                }
                printf "%d/%d/%d", value[1], value[2], value[3]
            }
        ') || return 1
        [ -n "$jobs_style_normalized" ]
    }
    # 查询可用不代表终端允许改色，按目标值核对实际生效结果。
    jobs_terminal_style_accepts_target() {
        jobs_style_requested_hex=''
        case $1 in
            10|12) jobs_style_requested_hex=ffffff ;;
            11) jobs_style_requested_hex=000000 ;;
            '4;'*)
                jobs_style_requested_index=0
                for jobs_style_requested_color in 000000 ff5f56 5fd787 ffd75f 5fafff d787ff 5fd7ff eeeeee 9e9e9e ff8787 87ffaf ffff87 87bfff ffafff afffff ffffff; do
                    if [ "4;$jobs_style_requested_index" = "$1" ]; then
                        jobs_style_requested_hex=$jobs_style_requested_color
                        break
                    fi
                    jobs_style_requested_index=$((jobs_style_requested_index + 1))
                done
                ;;
        esac
        [ -n "$jobs_style_requested_hex" ] || return 1
        printf '%s|%s\n' "$jobs_style_normalized" "$jobs_style_requested_hex" | LC_ALL=C awk -F'|' '
            function hexbyte(h) {
                return (index("0123456789abcdef", substr(h, 1, 1)) - 1) * 16 + index("0123456789abcdef", substr(h, 2, 1)) - 1
            }
            {
                if (split($1, actual, "/") != 3 || length($2) != 6) exit 1
                for (i = 1; i <= 3; i++) {
                    difference = actual[i] - hexbyte(substr($2, i * 2 - 1, 2)) * 257
                    if (difference < -255 || difference > 255) exit 1
                }
            }
        '
    }
    # 检测到后续改色时只恢复仍由本次保护持有的项，保留独立恢复入口。
    jobs_terminal_style_cleanup() {
        jobs_style_result=$1
        trap '' HUP INT TERM
        if [ "$jobs_style_query_active" = 1 ]; then
            stty "$jobs_style_stty" 2>/dev/null < /dev/tty || :
            jobs_style_query_active=0
        fi
        if [ "$jobs_style_changed" = 1 ]; then
            jobs_style_cleanup_ok=0
            jobs_style_conflicts=''
            jobs_style_restore_safe=''
            if [ "$jobs_style_applied_complete" = 1 ]; then
                jobs_style_stty=$(stty -g 2>/dev/null < /dev/tty) || jobs_style_stty=''
                if [ -n "$jobs_style_stty" ] && stty -echo -icanon min 0 time 1 2>/dev/null < /dev/tty; then
                    jobs_style_query_active=1
                    jobs_style_cleanup_ok=1
                    while IFS='|' read -r jobs_style_key jobs_style_expected jobs_style_original; do
                        [ -n "$jobs_style_key" ] || continue
                        if ! jobs_terminal_style_query "$jobs_style_key"; then
                            jobs_style_cleanup_ok=0
                            break
                        fi
                        if [ "$jobs_style_normalized" = "$jobs_style_expected" ]; then
                            jobs_style_restore_safe=$jobs_style_restore_safe$jobs_style_original
                        else
                            jobs_style_conflicts="$jobs_style_conflicts $jobs_style_key"
                        fi
                    done <<JOBS_STYLE_APPLIED
$jobs_style_applied_rows
JOBS_STYLE_APPLIED
                    stty "$jobs_style_stty" 2>/dev/null < /dev/tty || jobs_style_cleanup_ok=0
                    jobs_style_query_active=0
                fi
            fi
            if [ "$jobs_style_cleanup_ok" = 1 ] && printf '%s\033[0m' "$jobs_style_restore_safe" > /dev/tty; then
                if [ -z "$jobs_style_conflicts" ]; then
                    rm -f "$jobs_style_recovery"
                    rmdir "${jobs_style_recovery%/*}" 2>/dev/null || :
                else
                    printf '检测到运行期间的配色变更，已保留这些项：%s\n' "$jobs_style_conflicts" >&2
                    printf '确认要覆盖后续改色时才使用恢复入口：sh "%s"\n' "$jobs_style_recovery" >&2
                    [ "$jobs_style_result" -ne 0 ] || jobs_style_result=1
                fi
            else
                printf '终端配色未能安全自动恢复；确认覆盖当前配色后可运行：sh "%s"\n' "$jobs_style_recovery" >&2
                [ "$jobs_style_result" -ne 0 ] || jobs_style_result=1
            fi
        fi
        if [ "${2:-}" = continue ]; then
            jobs_style_cleanup_status=$jobs_style_result
            return 0
        fi
        exit "$jobs_style_result"
    }
    trap 'jobs_terminal_style_cleanup "$jobs_style_exit_status"' 0
    trap 'jobs_style_exit_status=129; exit 129' HUP
    trap 'jobs_style_exit_status=130; exit 130' INT
    trap 'jobs_style_exit_status=143; exit 143' TERM
    if ! stty -echo -icanon min 0 time 1 2>/dev/null < /dev/tty; then
        jobs_terminal_style_plain "$@"
    fi
    jobs_style_query_active=1
    jobs_style_probe_ok=1
    for jobs_style_key in 10 11 12 '4;0' '4;1' '4;2' '4;3' '4;4' '4;5' '4;6' '4;7' '4;8' '4;9' '4;10' '4;11' '4;12' '4;13' '4;14' '4;15'; do
        if ! jobs_terminal_style_query "$jobs_style_key"; then
            jobs_style_probe_ok=0
            break
        fi
        jobs_style_saved=$jobs_style_saved$jobs_style_reply
        jobs_style_saved_rows="$jobs_style_saved_rows$jobs_style_key|$jobs_style_reply
"
    done
    stty "$jobs_style_stty" 2>/dev/null < /dev/tty || { jobs_style_exit_status=1; exit 1; }
    jobs_style_query_active=0
    if [ "$jobs_style_probe_ok" != 1 ]; then
        printf '%s\n' '终端不支持完整配色保存，或启动时收到其它输入；保留原配色并使用纯文本。' >&2
        jobs_terminal_style_plain "$@"
    fi
    jobs_style_recovery_dir=$(umask 077; mktemp -d "${TMPDIR:-/tmp}/jobs-terminal-style.XXXXXX") || jobs_terminal_style_plain "$@"
    jobs_style_recovery=$jobs_style_recovery_dir/restore.sh
    if ! (umask 077; {
        printf '#!/bin/sh\n'
        printf '[ -t 0 ] && [ "$(tty)" = '\''%s'\'' ] || { printf '\''请在原终端运行恢复入口。\\n'\'' >&2; exit 1; }\n' "$jobs_style_tty"
        printf 'printf '\''本操作会覆盖此终端当前配色。确认恢复脚本启动前的配色，请输入 YES：'\'' >&2\n'
        printf 'IFS= read -r jobs_restore_choice\n[ "$jobs_restore_choice" = YES ] || exit 1\n'
        printf 'printf '\''%%s\\033[0m'\'' '\''%s'\'' > /dev/tty\n' "$jobs_style_saved"
    } > "$jobs_style_recovery"); then
        printf '%s\n' '无法保存终端配色恢复入口；保留原配色并使用纯文本。' >&2
        jobs_terminal_style_plain "$@"
    fi
    printf '正在准备本次终端临时配色；强退后恢复入口：sh "%s"\n' "$jobs_style_recovery" >&2
    jobs_style_changed=1
    printf '\033]10;#ffffff\007\033]11;#000000\007\033]12;#ffffff\007' > /dev/tty
    jobs_style_index=0
    for jobs_style_color in 000000 ff5f56 5fd787 ffd75f 5fafff d787ff 5fd7ff eeeeee 9e9e9e ff8787 87ffaf ffff87 87bfff ffafff afffff ffffff; do
        printf '\033]4;%s;#%s\007' "$jobs_style_index" "$jobs_style_color" > /dev/tty
        jobs_style_index=$((jobs_style_index + 1))
    done
    printf '\033[0m' > /dev/tty
    jobs_style_stty=$(stty -g 2>/dev/null < /dev/tty) || { jobs_style_exit_status=1; exit 1; }
    stty -echo -icanon min 0 time 1 2>/dev/null < /dev/tty || { jobs_style_exit_status=1; exit 1; }
    jobs_style_query_active=1
    jobs_style_probe_ok=1
    jobs_style_targets_ok=1
    while IFS='|' read -r jobs_style_key jobs_style_original; do
        [ -n "$jobs_style_key" ] || continue
        if ! jobs_terminal_style_query "$jobs_style_key"; then
            jobs_style_probe_ok=0
            break
        fi
        jobs_style_applied_rows="$jobs_style_applied_rows$jobs_style_key|$jobs_style_normalized|$jobs_style_original
"
        if ! jobs_terminal_style_accepts_target "$jobs_style_key"; then
            jobs_style_targets_ok=0
        fi
    done <<JOBS_STYLE_ORIGINAL
$jobs_style_saved_rows
JOBS_STYLE_ORIGINAL
    stty "$jobs_style_stty" 2>/dev/null < /dev/tty || { jobs_style_exit_status=1; exit 1; }
    jobs_style_query_active=0
    if [ "$jobs_style_probe_ok" != 1 ]; then
        printf '%s\n' '无法核实本次临时配色，已停止启动业务。' >&2
        jobs_style_exit_status=1
        exit 1
    fi
    jobs_style_applied_complete=1
    if [ "$jobs_style_targets_ok" != 1 ]; then
        jobs_terminal_style_cleanup 0 continue
        jobs_style_changed=0
        if [ "$jobs_style_cleanup_status" != 0 ]; then
            jobs_style_exit_status=1
            exit 1
        fi
        trap 'jobs_style_exit_status=129; exit 129' HUP
        trap 'jobs_style_exit_status=130; exit 130' INT
        trap 'jobs_style_exit_status=143; exit 143' TERM
        printf '%s\n' '终端未接受本次配色，已恢复原配色并使用纯文本。' >&2
        jobs_terminal_style_plain "$@"
    fi
    printf '%s\n' '本次终端已临时使用黑底白字。' >&2
    JOBS_TERMINAL_STYLE_TTY=$jobs_style_tty
    JOBS_TERMINAL_STYLE_OWNER=$$
    export JOBS_TERMINAL_STYLE_TTY JOBS_TERMINAL_STYLE_OWNER
    if "$@"; then
        jobs_style_exit_status=0
    else
        jobs_style_exit_status=$?
    fi
    exit "$jobs_style_exit_status"
}
"""
    _powershell_core = r"""$__jobsTerminalCommand = @($args)
# BEGIN JOBS_TERMINAL_STYLE_V1 - session-only colors; no profile or registry changes.
function New-JobsTerminalStyleState {
    if ($PSVersionTable.PSVersion.Major -lt 5) { return @{ JobsTerminalPlainFallback = $true; Before = @{} } }
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT -or $Host.Name -ne 'ConsoleHost') { return $null }
    if ([Console]::IsInputRedirected -or [Console]::IsOutputRedirected -or [Console]::IsErrorRedirected) { return $null }
    if ((Test-Path Env:NO_COLOR) -or $env:TERM -ieq 'dumb' -or $env:PLAIN_OUTPUT -eq '1') { return $null }
    foreach ($key in [Environment]::GetEnvironmentVariables().Keys) {
        if ([string]$key -match '^(?i:SOURCE_?TREE)') { return $null }
    }
    if (-not ('Jobs.TerminalStyleV1.Native' -as [type])) {
        try {
        Add-Type -ErrorAction Stop -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.RegularExpressions;
namespace Jobs.TerminalStyleV1 {
    public static class Native {
        [StructLayout(LayoutKind.Explicit, Size=20, CharSet=CharSet.Unicode)]
        public struct InputRecord {
            [FieldOffset(0)] public ushort Kind;
            [FieldOffset(4)] public int Down;
            [FieldOffset(8)] public ushort Repeat;
            [FieldOffset(10)] public ushort Key;
            [FieldOffset(12)] public ushort Scan;
            [FieldOffset(14)] public char Character;
            [FieldOffset(16)] public uint Modifiers;
        }
        [DllImport("kernel32.dll")] static extern IntPtr GetStdHandle(int n);
        [DllImport("kernel32.dll")] static extern IntPtr GetConsoleWindow();
        [DllImport("kernel32.dll")] static extern bool GetConsoleMode(IntPtr h, out uint mode);
        [DllImport("kernel32.dll")] static extern bool SetConsoleMode(IntPtr h, uint mode);
        [DllImport("kernel32.dll")] static extern uint WaitForSingleObject(IntPtr h, uint milliseconds);
        [DllImport("kernel32.dll")] static extern bool GetNumberOfConsoleInputEvents(IntPtr h, out uint count);
        [DllImport("kernel32.dll", CharSet=CharSet.Unicode, ExactSpelling=true)] static extern bool ReadConsoleInputW(IntPtr h, [Out] InputRecord[] records, uint count, out uint read);
        [DllImport("kernel32.dll", CharSet=CharSet.Unicode, ExactSpelling=true)] static extern bool WriteConsoleInputW(IntPtr h, InputRecord[] records, uint count, out uint written);
        const string OwnerName = "JOBS_TERMINAL_STYLE_WINDOWS_OWNER";
        static readonly string[] Keys = { "10", "11", "4;0", "4;1", "4;2", "4;3", "4;4", "4;5", "4;6", "4;7", "4;8", "4;9", "4;10", "4;11", "4;12", "4;13", "4;14", "4;15" };
        static readonly string[] Hex = { "000000", "ff5f56", "5fd787", "ffd75f", "5fafff", "d787ff", "5fd7ff", "eeeeee", "9e9e9e", "ff8787", "87ffaf", "ffff87", "87bfff", "ffafff", "afffff", "ffffff" };
        static readonly Regex Reply = new Regex("\\x1b\\](?<key>10|11|4;[0-9]{1,2});(?<rgb>rgb:[0-9a-f]{1,4}/[0-9a-f]{1,4}/[0-9a-f]{1,4})(?:\\x07|\\x1b\\\\)", RegexOptions.IgnoreCase);
        public sealed class State {
            public IntPtr Input, Output;
            public uint OutputMode;
            public ConsoleColor Foreground, Background;
            public Dictionary<string,string> Original, Applied;
            public string Owner, PreviousOwner, Recovery;
            public bool Active, ModeChanged, Fallback;
            public Dictionary<string,string> EnvironmentBefore = new Dictionary<string,string>();
        }
        static string Escape(string key, string value) { return "\x1b]" + key + ";" + value + "\x07"; }
        static string Rgb(string hex) { return "rgb:" + hex.Substring(0,2) + "/" + hex.Substring(2,2) + "/" + hex.Substring(4,2); }
        static string Normal(string rgb) {
            string[] parts = rgb.Substring(4).Split('/');
            for (int n=0; n<3; n++) {
                int maximum = (1 << (4 * parts[n].Length)) - 1;
                int value = Convert.ToInt32(parts[n],16);
                parts[n] = ((value * 65535L + maximum/2) / maximum).ToString("x4");
            }
            return String.Join("/",parts);
        }
        // Preserve unrelated key/window records instead of consuming user input during color queries.
        static Dictionary<string,string> Query(State state) {
            uint pending;
            if (!GetNumberOfConsoleInputEvents(state.Input,out pending) || pending != 0) { return null; }
            StringBuilder commands = new StringBuilder();
            foreach (string key in Keys) { commands.Append(Escape(key,"?")); }
            Console.Write(commands.ToString());
            List<InputRecord> records = new List<InputRecord>();
            List<int> characterIndices = new List<int>();
            StringBuilder text = new StringBuilder();
            Dictionary<string,string> result = new Dictionary<string,string>();
            Stopwatch timer = Stopwatch.StartNew();
            try {
                while (timer.ElapsedMilliseconds < 600) {
                    if (result.Count == Keys.Length && GetNumberOfConsoleInputEvents(state.Input,out pending) && pending == 0) { break; }
                    if (WaitForSingleObject(state.Input,20) != 0) { continue; }
                    InputRecord[] item = new InputRecord[1]; uint read;
                    if (!ReadConsoleInputW(state.Input,item,1,out read) || read != 1) { break; }
                    int index = -1;
                    if (item[0].Kind == 1 && item[0].Character != '\0') {
                        if (item[0].Down != 0) { index = text.Length; text.Append(item[0].Character); }
                        else if (text.Length != 0 && text[text.Length-1] == item[0].Character) { index = text.Length-1; }
                    }
                    records.Add(item[0]); characterIndices.Add(index);
                    foreach (Match match in Reply.Matches(text.ToString())) {
                        string key = match.Groups["key"].Value;
                        if (Array.IndexOf(Keys,key) >= 0) { result[key] = match.Groups["rgb"].Value; }
                    }
                }
            } finally {
                bool[] used = new bool[text.Length];
                foreach (Match match in Reply.Matches(text.ToString())) {
                    for (int n=match.Index; n<match.Index+match.Length; n++) { used[n] = true; }
                }
                List<InputRecord> replay = new List<InputRecord>();
                for (int n=0; n<records.Count; n++) {
                    int index = characterIndices[n];
                    if (index < 0 || !used[index]) { replay.Add(records[n]); }
                }
                if (replay.Count != 0) {
                    uint written;
                    if (!WriteConsoleInputW(state.Input,replay.ToArray(),(uint)replay.Count,out written) || written != replay.Count) {
                        Console.Error.WriteLine("[Jobs] Could not replay terminal input; color protection is unavailable.");
                        result.Clear();
                    }
                }
            }
            return result.Count == Keys.Length ? result : null;
        }
        static void Plain(State state) {
            foreach (string key in new string[] { "NO_COLOR", "PLAIN_OUTPUT", "FORCE_COLOR", "CLICOLOR", "ANSI_COLORS_DISABLED" }) {
                state.EnvironmentBefore[key] = Environment.GetEnvironmentVariable(key);
                Environment.SetEnvironmentVariable(key, key == "FORCE_COLOR" || key == "CLICOLOR" ? "0" : "1");
            }
            state.Fallback = true;
        }
        public static void Enter(State state) {
            try {
                state.Input = GetStdHandle(-10); state.Output = GetStdHandle(-11);
                uint inputMode;
                if (!GetConsoleMode(state.Input,out inputMode) || !GetConsoleMode(state.Output,out state.OutputMode)) { Plain(state); return; }
                IntPtr window = GetConsoleWindow();
                if (window == IntPtr.Zero) { Plain(state); return; }
                string identity = window.ToInt64().ToString("x");
                state.PreviousOwner = Environment.GetEnvironmentVariable(OwnerName);
                if (!String.IsNullOrEmpty(state.PreviousOwner)) {
                    string[] owner = state.PreviousOwner.Split(':');
                    int pid; long started;
                    if (owner.Length == 3 && owner[0] == identity && Int32.TryParse(owner[1],out pid) && Int64.TryParse(owner[2],out started)) {
                        try { if (Process.GetProcessById(pid).StartTime.ToUniversalTime().Ticks == started) { return; } } catch {}
                    }
                }
                state.Foreground = Console.ForegroundColor; state.Background = Console.BackgroundColor;
                if ((state.OutputMode & 4) == 0) {
                    if (!SetConsoleMode(state.Output,state.OutputMode | 4)) { Plain(state); return; }
                    state.ModeChanged = true;
                }
                state.Original = Query(state);
                if (state.Original == null) { Restore(state); Plain(state); return; }
                state.Applied = new Dictionary<string,string>();
                state.Applied["10"] = "rgb:ff/ff/ff"; state.Applied["11"] = "rgb:00/00/00";
                for (int n=0; n<16; n++) { state.Applied["4;"+n] = Rgb(Hex[n]); }
                StringBuilder restore = new StringBuilder();
                foreach (string key in Keys) { restore.Append(Escape(key,state.Original[key])); }
                string encoded = Convert.ToBase64String(Encoding.UTF8.GetBytes(restore.ToString()));
                state.Recovery = Path.Combine(Path.GetTempPath(),"JobsTerminalStyle-"+Process.GetCurrentProcess().Id+"-"+Guid.NewGuid().ToString("N")+".ps1");
                string manual = "# Restore only the session colors saved by this Jobs script.\r\n"+
                    "if ([Console]::IsOutputRedirected) { throw 'Run in the original console.' }\r\n"+
                    "Add-Type -Namespace Jobs -Name RecoveryConsole -MemberDefinition '[System.Runtime.InteropServices.DllImport(\"kernel32.dll\")] public static extern System.IntPtr GetStdHandle(int n); [System.Runtime.InteropServices.DllImport(\"kernel32.dll\")] public static extern bool GetConsoleMode(System.IntPtr h, out uint m); [System.Runtime.InteropServices.DllImport(\"kernel32.dll\")] public static extern bool SetConsoleMode(System.IntPtr h, uint m);'\r\n"+
                    "$h = [Jobs.RecoveryConsole]::GetStdHandle(-11); [uint32]$m = 0\r\n"+
                    "if (-not [Jobs.RecoveryConsole]::GetConsoleMode($h, [ref]$m)) { throw 'Run in the original console.' }\r\n"+
                    "try {\r\nif (-not [Jobs.RecoveryConsole]::SetConsoleMode($h, ($m -bor 4))) { throw 'Cannot enable terminal recovery.' }\r\n"+
                    "[Console]::Write([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('"+encoded+"')))\r\n"+
                    "[Console]::ForegroundColor = [ConsoleColor]"+((int)state.Foreground)+"\r\n"+
                    "[Console]::BackgroundColor = [ConsoleColor]"+((int)state.Background)+"\r\n"+
                    "[Console]::Write([string][char]27 + '[39;49m')\r\n"+
                    "} finally { [void][Jobs.RecoveryConsole]::SetConsoleMode($h, $m) }\r\n";
                File.WriteAllText(state.Recovery,manual,new UTF8Encoding(false));
                state.Owner = identity+":"+Process.GetCurrentProcess().Id+":"+Process.GetCurrentProcess().StartTime.ToUniversalTime().Ticks;
                Environment.SetEnvironmentVariable(OwnerName,state.Owner);
                state.Active = true;
                foreach (string key in Keys) { Console.Write(Escape(key,state.Applied[key])); }
                Console.ForegroundColor = ConsoleColor.White; Console.BackgroundColor = ConsoleColor.Black;
                Dictionary<string,string> check = Query(state);
                foreach (string key in Keys) {
                    if (check == null || Normal(check[key]) != Normal(state.Applied[key])) { Restore(state); Plain(state); return; }
                }
            } catch (Exception error) {
                Restore(state); Plain(state);
                Console.Error.WriteLine("[Jobs] Terminal style unavailable: " + error.Message);
            }
        }
        public static void Restore(State state) {
            if (state == null) { return; }
            try {
                if (state.Active) {
                    Dictionary<string,string> current = Query(state);
                    bool complete = current != null;
                    if (current != null) {
                        bool restoreForeground = Console.ForegroundColor == ConsoleColor.White && Normal(current["10"]) == Normal(state.Applied["10"]) && Normal(current["4;15"]) == Normal(state.Applied["4;15"]);
                        bool restoreBackground = Console.BackgroundColor == ConsoleColor.Black && Normal(current["11"]) == Normal(state.Applied["11"]) && Normal(current["4;0"]) == Normal(state.Applied["4;0"]);
                        foreach (string key in Keys) {
                            if (Normal(current[key]) == Normal(state.Applied[key])) { Console.Write(Escape(key,state.Original[key])); }
                            else if (Normal(current[key]) != Normal(state.Original[key])) {
                                complete = false; Console.Error.WriteLine("[Jobs] Kept a concurrent color change: " + key);
                            }
                        }
                        if (restoreForeground) { Console.ForegroundColor = state.Foreground; Console.Write("\x1b[39m"); }
                        if (restoreBackground) { Console.BackgroundColor = state.Background; Console.Write("\x1b[49m"); }
                    }
                    if (complete) {
                        Dictionary<string,string> check = Query(state);
                        foreach (string key in Keys) { if (check == null || Normal(check[key]) != Normal(state.Original[key])) { complete = false; } }
                    }
                    if (complete) { File.Delete(state.Recovery); }
                    else { Console.Error.WriteLine("[Jobs] Color restore needs review. Manual recovery: powershell -NoProfile -File \""+state.Recovery+"\""); }
                }
            } catch (Exception error) {
                Console.Error.WriteLine("[Jobs] Color restore failed: "+error.Message+"; recovery: "+state.Recovery);
            } finally {
                if (state.Owner != null && Environment.GetEnvironmentVariable(OwnerName) == state.Owner) { Environment.SetEnvironmentVariable(OwnerName,state.PreviousOwner); }
                state.Active = false;
                uint currentMode;
                if (state.ModeChanged && GetConsoleMode(state.Output,out currentMode) && currentMode == (state.OutputMode | 4)) { SetConsoleMode(state.Output,state.OutputMode); }
                state.ModeChanged = false;
                if (state.Fallback) {
                    foreach (KeyValuePair<string,string> pair in state.EnvironmentBefore) {
                        string applied = pair.Key == "FORCE_COLOR" || pair.Key == "CLICOLOR" ? "0" : "1";
                        if (Environment.GetEnvironmentVariable(pair.Key) == applied) { Environment.SetEnvironmentVariable(pair.Key,pair.Value); }
                    }
                    state.Fallback = false;
                }
            }
        }
    }
}
'@
        } catch {
            [Console]::Error.WriteLine('[Jobs] Terminal style setup failed; using plain output: ' + $_.Exception.Message)
            return @{ JobsTerminalPlainFallback = $true; Before = @{} }
        }
    }
    return New-Object Jobs.TerminalStyleV1.Native+State
}
# Guard setup is optional; failure keeps business behavior and the user's original terminal settings.
function Start-JobsTerminalStyle {
    param($State)
    if ($State -is [Collections.IDictionary] -and $State.Contains('JobsTerminalPlainFallback')) {
        foreach ($key in @('NO_COLOR', 'PLAIN_OUTPUT', 'FORCE_COLOR', 'CLICOLOR', 'ANSI_COLORS_DISABLED')) {
            $State.Before[$key] = [Environment]::GetEnvironmentVariable($key)
            [Environment]::SetEnvironmentVariable($key, $(if (@('FORCE_COLOR', 'CLICOLOR') -contains $key) { '0' } else { '1' }))
        }
        return
    }
    if ($null -ne $State) { [Jobs.TerminalStyleV1.Native]::Enter($State) }
}
# A finally block also runs for script exit and Ctrl+C; direct .NET calls avoid stopped pipelines.
function Stop-JobsTerminalStyle {
    param($State)
    if ($State -is [Collections.IDictionary] -and $State.Contains('JobsTerminalPlainFallback')) {
        foreach ($key in $State.Before.Keys) {
            $applied = if (@('FORCE_COLOR', 'CLICOLOR') -contains $key) { '0' } else { '1' }
            if ([Environment]::GetEnvironmentVariable($key) -ceq $applied) { [Environment]::SetEnvironmentVariable($key, $State.Before[$key]) }
        }
        return
    }
    if ($null -ne $State) { [Jobs.TerminalStyleV1.Native]::Restore($State) }
}
# END JOBS_TERMINAL_STYLE_V1

$__jobsTerminalStyleState = $null
$__jobsTerminalExitCode = 0
try {
    $__jobsTerminalStyleState = New-JobsTerminalStyleState
    Start-JobsTerminalStyle $__jobsTerminalStyleState
    if ($null -eq $__jobsTerminalCommand -or $__jobsTerminalCommand.Count -eq 0) { throw 'A program is required.' }
    $__jobsTerminalProgram = $__jobsTerminalCommand[0]
    $__jobsTerminalArguments = @()
    if ($__jobsTerminalCommand.Count -gt 1) { $__jobsTerminalArguments = @($__jobsTerminalCommand[1..($__jobsTerminalCommand.Count-1)]) }
    $LASTEXITCODE = 0
    & $__jobsTerminalProgram @__jobsTerminalArguments
    $__jobsTerminalCommandSucceeded = $?
    $__jobsTerminalExitCode = $LASTEXITCODE
    if (-not $__jobsTerminalCommandSucceeded -and $__jobsTerminalExitCode -eq 0) { $__jobsTerminalExitCode = 1 }
} finally {
    Stop-JobsTerminalStyle $__jobsTerminalStyleState
}
exit $__jobsTerminalExitCode
"""
    _interrupted = False
    # 等监督进程完成恢复后再退出，避免 Ctrl+C 提前关闭控制终端。
    def _wait(_arguments):
        nonlocal _interrupted
        _process = _subprocess.Popen(_arguments, env=_environment)
        while True:
            try:
                return _process.wait()
            except KeyboardInterrupt:
                _interrupted = True
                continue
    try:
        if _os.name == "nt":
            _powershell = _shutil.which("powershell.exe") or _shutil.which("pwsh.exe")
            if not _powershell:
                _os.environ.update(NO_COLOR="1", PLAIN_OUTPUT="1", FORCE_COLOR="0", CLICOLOR="0")
                return
            with _tempfile.TemporaryDirectory(prefix="jobs-terminal-style-") as _directory:
                _wrapper = _os.path.join(_directory, "guard.ps1")
                with open(_wrapper, "w", encoding="utf-8-sig", newline="\n") as _file:
                    _file.write(_powershell_core)
                # 原参数经 JSON 交给原生 Python 数组，避开旧 Windows PowerShell 的参数重解析。
                _environment["JOBS_TERMINAL_STYLE_PYTHON_COMMAND"] = _json.dumps(_command, ensure_ascii=False)
                _receipt = _os.path.join(_directory, "started")
                _environment["JOBS_TERMINAL_STYLE_PYTHON_RECEIPT"] = _receipt
                _bridge_source = """import json, os, subprocess, sys
command = json.loads(os.environ.pop('JOBS_TERMINAL_STYLE_PYTHON_COMMAND'))
with open(os.environ.pop('JOBS_TERMINAL_STYLE_PYTHON_RECEIPT'), 'wb') as receipt:
    receipt.write(b'started')
process = subprocess.Popen(command)
while True:
    try:
        result = process.wait()
        break
    except KeyboardInterrupt:
        continue
sys.exit(result if result >= 0 else 128 - result)
"""
                _bridge = "exec(__import__('base64').b64decode('" + _base64.b64encode(_bridge_source.encode()).decode() + "'))"
                _result = _wait([_powershell, "-NoProfile", "-ExecutionPolicy", "Bypass",
                                 "-File", _wrapper, _sys.executable, "-c", _bridge])
                if not _os.path.exists(_receipt) and not _interrupted and _result not in (129, 130, 143, -1073741510, 0xC000013A):
                    _os.environ.update(NO_COLOR="1", PLAIN_OUTPUT="1", FORCE_COLOR="0", CLICOLOR="0")
                    print("终端配色保护未能启动，保持原配色并使用纯文本。", file=_sys.stderr)
                    return
        else:
            _result = _wait(["/bin/sh", "-c", _shell_core + '\njobs_terminal_style_run "$@"\n',
                             "jobs-terminal-style", *_command])
    except KeyboardInterrupt:
        raise SystemExit(130) from None
    except OSError:
        _os.environ.update(NO_COLOR="1", PLAIN_OUTPUT="1", FORCE_COLOR="0", CLICOLOR="0")
        print("终端配色保护未能启动，保持原配色并使用纯文本。", file=_sys.stderr)
        return
    if _result in (-1073741510, 0xC000013A):
        raise SystemExit(130)
    raise SystemExit(_result if _result >= 0 else 128 - _result)


if __name__ == "__main__":
    _jobs_terminal_style_bootstrap_v1()
# JOBS_TERMINAL_STYLE_GUARD_V1_END

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
