@echo off
setlocal
cd /d "%~dp0.."
where py >nul 2>nul
if errorlevel 1 (
  python scripts\master_editor.py
) else (
  py -3 scripts\master_editor.py
)
if errorlevel 1 pause
