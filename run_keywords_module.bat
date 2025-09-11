@echo off
setlocal
cd /d "%~dp0"

REM --- pick python ---
where py >nul 2>&1
if %errorlevel%==0 (
  set "PY=py -3"
) else (
  where python >nul 2>&1
  if %errorlevel%==0 (
    set "PY=python"
  ) else (
    echo [X] Python not found. Install Python or add it to PATH.
    pause
    exit /b 1
  )
)

REM --- global used keywords file (CHANGE THIS to your real path) ---
if not defined NB_USED_GLOBAL set "NB_USED_GLOBAL=D:\project\used_keywords_global.txt"

echo [1/4] build keywords (Google Suggest)
%PY% -u keywords_builder_google_only.py || goto :ERR

echo [2/4] enrich keywords (optional)
%PY% -u enrich_keywords.py || echo [WARN] enrich failed; continue...

echo [3/4] select keywords with cross-site dedup
set "NB_USED_GLOBAL=%NB_USED_GLOBAL%"
%PY% -u select_keywords.py || goto :ERR

echo [4/4] inject into pages
if not exist ".nb_injected.flag" (
  %PY% -u inject_keywords.py --force || goto :ERR
  type nul > ".nb_injected.flag"
) else (
  %PY% -u inject_keywords.py || goto :ERR
)

echo.
echo [OK] done.
pause
exit /b 0

:ERR
echo.
echo [ERR] step failed. ErrorLevel=%ERRORLEVEL%
pause
exit /b 1
