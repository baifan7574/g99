@echo off
chcp 65001 >nul
echo ============================================
echo   🧩 NorthBeam - BlackBox Variant Injector
echo ============================================

REM 运行黑框补丁脚本
python patch_nb_variants.py --site-root . --modules-per-page 2 --salt 2025

echo [OK] 黑框补丁已注入完成
echo.
pause
