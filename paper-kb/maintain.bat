@echo off
rem paper-kb 維護：雙擊執行。第一次會自動建立 .venv（需要 Python 3.11 以上）
rem 其他用法：maintain.bat --install-claude ／ maintain.bat --schedule weekly ／ maintain.bat --check
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo 第一次執行：建立 Python 環境 .venv ...
  py -3.12 -m venv .venv 2>nul || py -3.11 -m venv .venv 2>nul || python -m venv .venv
  if not exist ".venv\Scripts\python.exe" (
    echo 找不到 Python 3.11 以上。請先從 https://www.python.org/downloads/ 安裝，再雙擊一次。
    pause
    exit /b 1
  )
  ".venv\Scripts\python.exe" -m pip install -q --upgrade pip
)
".venv\Scripts\python.exe" maintain.py %*
