# -*- coding: utf-8 -*-
"""paper-kb 維護程式：安裝、更新、健康檢查、接上 Claude Desktop、排程，一支搞定

Windows 直接雙擊 maintain.bat（會自動建立 .venv 並用它跑本程式）。

  python maintain.py                    更新資料（inbox → 解析 → 索引）＋健康檢查，結果寫進 data/derived/health.md
  python maintain.py --check            只做健康檢查
  python maintain.py --install-claude   把 paper-kb 加進 Claude Desktop 設定（會先備份原設定）
  python maintain.py --schedule weekly  設定排程自動維護（daily / weekly / off）。Windows 用工作排程器
  python maintain.py --minutes 2        整體最多跑 2 分鐘（沒做完的下次接著做）
  python maintain.py --quiet            排程用：不等使用者按鍵、只寫紀錄

同一時間只會有一個維護在跑（data/derived/.maintain.lock；超過 6 小時視為殘留，自動清掉）。
"""
import os
import re
import sys
import json
import time
import shutil
import sqlite3
import platform
import datetime
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
DER = os.path.join(ROOT, 'data', 'derived')
DB = os.path.join(DER, 'index', 'papers.db')
LOCK = os.path.join(DER, '.maintain.lock')
LOG = os.path.join(DER, 'maintain_log.md')
HEALTH = os.path.join(DER, 'health.md')
TASK_NAME = 'paper-kb-maintain'
args = sys.argv[1:]


def opt(name, default=None):
    return args[args.index(name) + 1] if name in args and args.index(name) + 1 < len(args) else default


QUIET = '--quiet' in args
out_lines = []


def say(msg=''):
    print(msg, flush=True)
    out_lines.append(msg)


# ---------------- 安裝 ----------------
def ensure_deps():
    """缺套件就裝進目前這個 Python（maintain.bat 會先建立 .venv，所以裝在專案自己的環境裡）"""
    if sys.version_info < (3, 11):
        say(f'⚠️ 目前 Python {platform.python_version()}；解析 PDF 需要 3.11 以上（pymupdf4llm 2.1）。'
            f'只用 server 的話 3.10 也可以。')
    missing = []
    for mod in ('mcp', 'pymupdf4llm'):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if not missing:
        return True
    say(f'安裝缺少的套件：{", ".join(missing)}')
    r = subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '-r', os.path.join(ROOT, 'requirements.txt')])
    if r.returncode != 0:
        say('❌ 套件安裝失敗：請檢查網路，或手動執行 pip install -r requirements.txt')
        return False
    # 新裝的套件（例如 Windows 上 mcp 需要的 pywin32）要重新啟動 Python 才會生效 → 重新執行自己一次
    if not os.environ.get('PAPER_KB_REEXEC'):
        say('套件裝好了，重新啟動維護程式…')
        os.environ['PAPER_KB_REEXEC'] = '1'
        sys.exit(subprocess.call([sys.executable, os.path.abspath(__file__)] + args))
    return True


# ---------------- 鎖 ----------------
def acquire_lock():
    os.makedirs(DER, exist_ok=True)
    if os.path.exists(LOCK) and os.path.getsize(LOCK) > 0:   # 空檔 = 上次已正常解鎖（有些磁碟不能刪檔）
        age = time.time() - os.path.getmtime(LOCK)
        if age < 6 * 3600:
            say(f'另一個維護正在進行（{age / 60:.0f} 分鐘前開始）；這次先跳過。若確定沒有在跑，刪掉 {LOCK}')
            return False
        say('清除殘留的鎖（超過 6 小時）')
    with open(LOCK, 'w') as f:
        f.write(f'{os.getpid()} {datetime.datetime.now().isoformat(timespec="seconds")}')
    return True


def release_lock():
    try:
        os.remove(LOCK)
    except OSError:
        try:   # 有些掛載磁碟不能刪檔：改成清空並把時間設成很久以前
            open(LOCK, 'w').close(); os.utime(LOCK, (0, 0))
        except OSError:
            pass


# ---------------- 更新 ----------------
def run_update(budget_min):
    """反覆呼叫 update.py，直到沒有待解析的文件、時間用完、或沒有進展"""
    t0 = time.time()
    workers = opt('--workers') or str(max(1, min(4, (os.cpu_count() or 2) // 2)))
    last_left = None
    for rnd in range(1, 50):
        left_min = None if budget_min is None else budget_min - (time.time() - t0) / 60
        if left_min is not None and left_min < 0.5:
            say('⏸ 時間用完，剩下的下次維護再做'); break
        cmd = [sys.executable, '-u', os.path.join(ROOT, 'update.py'), '--workers', workers, '--doc-timeout', '300']
        if left_min is not None:
            cmd += ['--minutes', f'{max(0.3, left_min - 0.6):.1f}']
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
        lines = [l for l in r.stdout.splitlines() if l.strip() and not re.match(r'\s*\[\d+/\d+\]', l)
                 and not re.search(r'OCR|Tesseract|^=+$', l)]
        for l in lines:
            say('  ' + l.strip())
        if r.returncode != 0:
            say('❌ update.py 出錯：\n' + '\n'.join(r.stderr.strip().splitlines()[-8:])); return False
        m = re.search(r'剩 (\d+) 份下次', r.stdout)
        left = int(m.group(1)) if m else 0
        if left == 0:
            return True
        if left == last_left:
            say('⚠️ 沒有進展，停止'); return False
        last_left = left
    return True


# ---------------- 健康檢查 ----------------
def health():
    import csv
    sys.path.insert(0, os.path.join(ROOT, 'src'))
    problems, info = [], []
    reg_path = os.path.join(DER, 'registry.csv')
    rows = list(csv.DictReader(open(reg_path, encoding='utf-8-sig'))) if os.path.exists(reg_path) else []
    canon = [r for r in rows if r['canonical'] == 'True']
    failed = [r for r in canon if r['parsed_ver'] in ('ERR', 'TIMEOUT')]
    inbox = [f for f in os.listdir(os.path.join(ROOT, 'input_raw', 'inbox')) if not f.startswith('.')] \
        if os.path.isdir(os.path.join(ROOT, 'input_raw', 'inbox')) else []
    info.append(f'PDF {len(rows)} 個、去重後 {len(canon)} 份')
    if inbox:
        problems.append(f'inbox 還有 {len(inbox)} 個檔案沒處理（再跑一次維護）')
    qf = os.path.join(ROOT, 'input_raw', 'url_queue.txt')
    queued = [l for l in open(qf, encoding='utf-8') if l.strip() and not l.startswith('#')] if os.path.exists(qf) else []
    if queued:
        problems.append(f'url_queue.txt 還有 {len(queued)} 個網址沒下載成功（檢查網路後再跑一次維護）')
    for r in failed:
        problems.append(f'解析{"逾時" if r["parsed_ver"] == "TIMEOUT" else "失敗"}：{r["path"]}'
                        f'（可用 python update.py --retry-failed --doc-timeout 1200 重試）')
    if not os.path.exists(DB):
        problems.append('找不到索引 papers.db（先跑一次維護）')
    else:
        try:
            from paper_kb import index
            db = index.connect(DB, readonly=True)
            ok = db.execute('PRAGMA quick_check').fetchone()[0]
            n_doc = db.execute('SELECT COUNT(*) FROM docs').fetchone()[0]
            n_para = db.execute('SELECT COUNT(*) FROM paras').fetchone()[0]
            n_cite = db.execute('SELECT COUNT(*) FROM cites').fetchone()[0]
            # 測試搜尋：從索引裡隨便取一個英文字來搜（不依賴特定主題，任何人的論文庫都適用）
            import re as _re
            _row = db.execute("SELECT text FROM paras WHERE kind = 'text' LIMIT 1").fetchone()
            _w = _re.findall(r'[A-Za-z]{5,}', _row[0]) if _row else []
            hits = index.search(db, _w[0], k=3) if _w else [None]   # 空索引：不算錯
            db.close()
            info.append(f'索引：{n_doc} 份、{n_para} 段、引用關係 {n_cite} 筆、檔案 {os.path.getsize(DB) / 1e6:.0f} MB')
            if ok != 'ok':
                problems.append(f'索引損壞（{ok}）：請跑 python update.py --rebuild')
            if n_doc < len(canon) - len(failed):
                problems.append(f'索引只有 {n_doc} 份，應有 {len(canon) - len(failed)} 份（再跑一次維護）')
            if not hits:
                problems.append('測試搜尋沒有結果')
        except Exception as e:
            problems.append(f'無法開啟索引：{type(e).__name__}: {e}')
    # 用另一個 Python 載入 server（和 Claude Desktop 啟動它的方式一樣）
    r = subprocess.run([sys.executable, '-c', 'import paper_kb.server'], capture_output=True, text=True,
                       env={**os.environ, 'PYTHONPATH': os.path.join(ROOT, 'src'), 'PAPER_KB_ROOT': ROOT})
    if r.returncode == 0:
        info.append('MCP server：可載入')
    else:
        err = (r.stderr.strip().splitlines() or ['?'])[-1]
        hint = '（Windows：試試 .venv\\Scripts\\python -m pip install --force-reinstall pywin32）' if 'pywin' in err else ''
        problems.append(f'MCP server 無法載入：{err}{hint}')
    found, default = claude_config_paths()
    if default is not None:
        if not any(os.path.exists(c) for c in found):
            info.append('Claude Desktop：還沒有設定檔 → 執行 maintain.bat --install-claude')
        for cfg in found:
            if not os.path.exists(cfg):
                continue
            try:
                on = 'paper-kb' in json.load(open(cfg, encoding='utf-8')).get('mcpServers', {})
                info.append(f'Claude Desktop（{cfg}）：{"已設定 paper-kb" if on else "未設定 → 執行 maintain.bat --install-claude"}')
            except Exception:
                info.append(f'Claude Desktop（{cfg}）：設定檔不是有效的 JSON')
    return problems, info


# ---------------- Claude Desktop ----------------
def claude_config_paths():
    """Claude Desktop 設定檔可能的位置（一般安裝版、Microsoft Store 版）。回傳 (已存在的, 預設位置)"""
    import glob
    sysname = platform.system()
    if sysname == 'Windows':
        default = os.path.join(os.environ.get('APPDATA', ''), 'Claude', 'claude_desktop_config.json')
        dirs = [os.path.join(os.environ.get('APPDATA', ''), 'Claude')]
        dirs += glob.glob(os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Packages', '*Claude*',
                                       'LocalCache', 'Roaming', 'Claude'))
    elif sysname == 'Darwin':
        default = os.path.expanduser('~/Library/Application Support/Claude/claude_desktop_config.json')
        dirs = [os.path.dirname(default)]
    else:
        return [], None
    found = [os.path.join(d, 'claude_desktop_config.json') for d in dirs
             if os.path.isdir(d)]          # Claude 資料夾存在就算（設定檔可能還沒建立）
    return found, default


def install_claude():
    found, default = claude_config_paths()
    if default is None:
        say('這台不是 Windows / macOS，沒有 Claude Desktop 設定檔。其他 client 請看 README。'); return
    targets = found or [default]
    entry = {
        'command': sys.executable,
        'args': ['-m', 'paper_kb.server'],
        'env': {'PYTHONPATH': os.path.join(ROOT, 'src'), 'PAPER_KB_ROOT': ROOT},
    }
    for cfg in targets:
        os.makedirs(os.path.dirname(cfg), exist_ok=True)
        data = {}
        if os.path.exists(cfg):
            bak = cfg + f'.bak_{datetime.datetime.now():%y%m%d_%H%M%S}'
            shutil.copy2(cfg, bak); say(f'已備份原設定：{bak}')
            try:
                data = json.load(open(cfg, encoding='utf-8'))
            except Exception:
                say(f'⚠️ 原設定不是有效的 JSON，已備份，改寫成新的'); data = {}
        data.setdefault('mcpServers', {})['paper-kb'] = entry
        json.dump(data, open(cfg, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
        say(f'✅ 已把 paper-kb 寫進 {cfg}')
    say('   接著「完全結束」Claude Desktop（系統匣圖示按右鍵 → 結束）再打開。')


# ---------------- 排程 ----------------
def schedule(when):
    s = platform.system()
    if s == 'Windows':
        bat = os.path.join(ROOT, 'maintain.bat')
        if when == 'off':
            r = subprocess.run(['schtasks', '/Delete', '/TN', TASK_NAME, '/F'], capture_output=True, text=True)
            say('✅ 已取消排程' if r.returncode == 0 else f'取消失敗：{r.stderr.strip()}'); return
        sc = {'daily': ['/SC', 'DAILY'], 'weekly': ['/SC', 'WEEKLY', '/D', 'SUN']}[when]
        r = subprocess.run(['schtasks', '/Create', '/F', '/TN', TASK_NAME, '/TR', f'"{bat}" --quiet', '/ST', '13:07'] + sc,
                           capture_output=True, text=True)
        if r.returncode == 0:
            say(f'✅ 已設定排程「{TASK_NAME}」：{"每天" if when == "daily" else "每週日"} 13:07 自動維護'
                f'（電腦要開著；結果看 data/derived/health.md）')
        else:
            say(f'排程設定失敗：{r.stderr.strip() or r.stdout.strip()}')
    else:
        cron = {'daily': '7 13 * * *', 'weekly': '7 13 * * 0'}.get(when)
        say('請用 crontab -e 加入這行：\n' + (f'{cron} cd "{ROOT}" && "{sys.executable}" maintain.py --quiet' if cron
                                         else '（取消：刪掉 crontab 裡含 maintain.py 的那行）'))


# ---------------- 主程式 ----------------
def main():
    if '--install-claude' in args:
        install_claude(); return 0
    if '--schedule' in args:
        schedule(opt('--schedule', 'weekly')); return 0
    start = datetime.datetime.now()
    say(f'# paper-kb 維護 {start:%Y-%m-%d %H:%M}')
    ok = True
    if '--check' not in args:
        if not ensure_deps():
            return 1
        if not acquire_lock():
            return 0
        try:
            budget = float(opt('--minutes')) if opt('--minutes') else None
            ok = run_update(budget)
        finally:
            release_lock()
    problems, info = health()
    say('\n## 健康檢查')
    for l in info:
        say(f'- {l}')
    say('- ✅ 一切正常' if not problems and ok else '')
    for p in problems:
        say(f'- ⚠️ {p}')
    os.makedirs(DER, exist_ok=True)
    body = '\n'.join(out_lines) + f'\n\n（{(datetime.datetime.now() - start).seconds} 秒）\n'
    open(HEALTH, 'w', encoding='utf-8').write(body)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write('\n' + body)
    return 0 if ok and not problems else 2


if __name__ == '__main__':
    code = main()
    if platform.system() == 'Windows' and not QUIET and sys.stdin and sys.stdin.isatty():
        input('\n按 Enter 關閉')
    sys.exit(code)
