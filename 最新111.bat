@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
echo ✅ 当前终端编码：UTF-8

REM ===== 日志目录 =====
if not exist "%~dp0logs" mkdir "%~dp0logs"

REM ===== 1) 生成图片（原流程） =====
cd /d "%~dp0generator"
echo 🖼️ 正在批量生成图片...
call run_generator_autopath.bat

REM ===== 2) 回主目录，网页生成 + SEO结构（原流程） =====
cd ..
echo 🌐 正在执行网页生成 + SEO 插入...
call run_all.bat

REM ===== 3) 插入广告（原流程） =====
echo 💰 正在插入广告...
python ads_apply_all.py

REM ===== 4) v4 修复（原流程） =====
echo 🔧 正在执行 SEO 修复 v4...
python seo_fixer_v4.py

REM ===== 5) 补丁（固定使用 v4_patch_single_site.py） =====
echo 🩹 正在执行补丁 v4_patch_single_site.py...
if exist "%~dp0v4_patch_single_site.py" (
  python "%~dp0v4_patch_single_site.py"
) else (
  echo ❌ 未找到补丁：%~dp0v4_patch_single_site.py
)

REM ===== 6) 上传（原流程） =====
echo 🚀 正在上传到 GitHub 仓库...
python auto_git_push.py

REM ===== 7) 自动读取 domain 并 Ping 地图（带检测与重试） =====
for /f "usebackq tokens=* delims=" %%i in (`
  powershell -NoProfile -Command ^
    "$d=(Get-Content '%~dp0config.json' -Raw | ConvertFrom-Json).domain; if($d){$d.TrimEnd('/')}"
`) do set DOMAIN=%%i

if "%DOMAIN%"=="" (
  echo ❌ 未能从 config.json 读取 domain，跳过 Ping。
  goto :END
)

set "SITEMAP_URL=%DOMAIN%/sitemap.xml"
echo 🌍 准备 Ping：%SITEMAP_URL%

REM 仅当本地有 sitemap.xml 才尝试 Ping（避免空打）
if not exist "%~dp0sitemap.xml" (
  echo ⚠️ 本地未发现 sitemap.xml，建议让 v4 产出或手动生成后再 Ping。
  goto :END
)

REM 等待部署就绪：HEAD 探测 6 次（每次 10s）
powershell -NoProfile -Command ^
  "$u='%SITEMAP_URL%'; $ok=$false; for($i=1;$i -le 6;$i++){ try{ $r=Invoke-WebRequest -UseBasicParsing -Uri $u -Method Head -TimeoutSec 20; if($r.StatusCode -eq 200){$ok=$true; break} }catch{}; Start-Sleep -Seconds 10 }; if($ok){'OK'}" > "%~dp0logs\sitemap_probe.tmp"
set /p PROBE=<"%~dp0logs\sitemap_probe.tmp"
del "%~dp0logs\sitemap_probe.tmp" >nul 2>&1

if not "%PROBE%"=="OK" (
  echo ⚠️ 部署可能未完全就绪，先尝试 Ping（如返回 404，稍后可再单独补 Ping）。
)

REM 正式 Ping（Google + Bing），各重试 3 次
powershell -NoProfile -Command ^
  "$u='%SITEMAP_URL%'; $eps=@('https://www.google.com/ping?sitemap=','https://www.bing.com/ping?sitemap=');" ^
  "foreach($e in $eps){ for($i=1;$i -le 3; $i++){ try{ $r=Invoke-WebRequest -UseBasicParsing -Uri ($e + [uri]::EscapeDataString($u)) -TimeoutSec 20; Write-Host ('PING '+$e+' -> '+$r.StatusCode); if($r.StatusCode -eq 200){ break } } catch { Write-Host ('PING '+$e+' FAIL try'+$i+': '+$_.Exception.Message) } Start-Sleep -Seconds 5 } }"

echo ✅ 全部流程执行完毕！
:END
pause
endlocal
