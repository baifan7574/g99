@echo off
chcp 65001 >nul
echo ============================================
echo   🚀 NorthBeam Studio - Master Run (No Build)
echo ============================================
echo.

REM 1) 生成图片（进入 generator 子目录运行，再回到根目录）
pushd generator
call run_generator_autopath.bat
popd
echo [OK] 图片生成完成
echo.

REM 2) 网页生成（在根目录）
call run_all.bat
echo [OK] 网页生成完成
echo.

REM 3) 差异化增强
python site_enhance_all.py
echo [OK] 差异化增强完成
echo.

REM 4) 广告注入
python ads_apply_all.py
echo [OK] 广告注入完成
echo.

REM 5) SEO 修复
python seo_fixer_v4.py
echo [OK] SEO 修复完成
echo.

REM 6) 单站补丁
python v4_patch_single_site.py
echo [OK] 单站补丁完成
echo.

REM 7) 关键词注入（只保留注入+持久化）
python inject_keywords.py
python kw_persist_and_fill.py
echo [OK] 关键词注入完成
echo.

REM 8) Sitemap 修复
python sitemap_fix.py
echo [OK] Sitemap 修复完成
echo.

REM 9) GitHub 推送
python auto_git_push.py
echo [OK] GitHub 推送完成
echo.

REM 10) Ping 搜索引擎
python seo_ping_guard_v2.py
echo [OK] Sitemap Ping 完成
echo.

echo ============================================
echo   ✅ 全流程执行完成（不包含找词）
echo ============================================
pause
