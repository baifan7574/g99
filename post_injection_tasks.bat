@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
cd /d "%~dp0"

where py >nul 2>nul && (set "PY=py -3") || (set "PY=python")

echo [POST] 1) site_enhance_all.py —— 结构差异化（专题、相关推荐、分类文案等）
if exist "site_enhance_all.py" (
  %PY% -u site_enhance_all.py
) else (
  echo [SKIP] 找不到 site_enhance_all.py
)

echo [POST] 2) sitemap_fix.py —— 重新生成最终 sitemap.xml
if exist "sitemap_fix.py" (
  %PY% -u sitemap_fix.py
) else (
  echo [SKIP] 找不到 sitemap_fix.py
)

echo [POST] 3) seo_error_checker.py —— 事后体检，出报告不改文件
if exist "seo_error_checker.py" (
  %PY% -u seo_error_checker.py --root "%~dp0"
) else (
  echo [SKIP] 找不到 seo_error_checker.py
)

echo [POST] ✅ done
endlocal
