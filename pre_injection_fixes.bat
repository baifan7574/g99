@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
cd /d "%~dp0"

REM ===== 预处理补丁（在关键词注入之前执行）=====
REM 作用：只“补缺不覆盖”，避免后面关键词被顶掉

where py >nul 2>nul && (set "PY=py -3") || (set "PY=python")

echo [PRE] 1) seo_fixer_v4.py  —— 填补缺失的 title/description/alt/canonical/JSON-LD/内链
if exist "seo_fixer_v4.py" (
  %PY% -u seo_fixer_v4.py
) else (
  echo [SKIP] 找不到 seo_fixer_v4.py
)

echo [PRE] 2) v4_patch_single_site.py —— 仅在“不合格”(太短/缺失)时修复标题/描述/正文，并修正 canonical/schema
if exist "v4_patch_single_site.py" (
  %PY% -u v4_patch_single_site.py
) else (
  echo [SKIP] 找不到 v4_patch_single_site.py
)

echo [PRE] ✅ done
endlocal
