@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
echo ✅ 当前终端编码：UTF-8

REM ===== 1) 生成图片（你的原流程） =====
cd /d "%~dp0generator"
echo 🖼️ 正在批量生成图片...
call run_generator_autopath.bat

REM ===== 2) 回主目录，网页生成 + SEO结构（你的原流程） =====
cd ..
echo 🌐 正在执行网页生成 + SEO 插入...
call run_all.bat

REM ===== 2.5) 结构+文案差异化补丁（Slogan / 分类描述 / 专题页 / 相关推荐） =====
cd /d "%~dp0"
echo 🧩 正在执行站点差异化补丁（site_enhance_all.py）...

REM 确认脚本存在
if not exist "%~dp0site_enhance_all.py" (
  echo ❌ 未发现 site_enhance_all.py ，跳过本步骤。
  goto :AFTER_ENHANCE
)

REM 可选：存在配置则提示（不强制）
if exist "%~dp0site_structure_config.json" echo 🔧 读取 site_structure_config.json...
if exist "%~dp0slogans.txt" echo 🔤 读取 slogans.txt...
if exist "%~dp0category_desc_templates.txt" echo 🧱 读取 category_desc_templates.txt...

python site_enhance_all.py
if errorlevel 1 (
  echo ⚠️ 差异化补丁返回非 0（请检查输出），继续后续流程...
) else (
  echo ✅ 差异化补丁执行完成。
)

:AFTER_ENHANCE


REM ===== 3) 插入广告（你的原流程） =====
echo 💰 正在插入广告...
python ads_apply_all.py

REM ===== 4) v4 修复（你的原流程） =====
echo 🔧 正在执行 SEO 修复 v4...
python seo_fixer_v4.py

REM ===== 5) 补丁（固定执行 v4_patch_single_site.py） =====
echo 🩹 正在执行补丁 v4_patch_single_site.py...
if exist "%~dp0v4_patch_single_site.py" (
  python "%~dp0v4_patch_single_site.py"
) else (
  echo ❌ 未找到补丁：%~dp0v4_patch_single_site.py
)

REM ===== 5.4) 如果没有 keywords\selected.txt，则自动用 selected_keywords\*.txt 合并生成（不覆盖已有文件） =====
if not exist "keywords" mkdir "keywords"
if not exist "keywords\selected.txt" if exist "selected_keywords" (
  for %%F in ("selected_keywords\*.txt") do (
    type "%%~F" >> "keywords\selected.tmp"
  )
  if exist "keywords\selected.tmp" (
    type "keywords\selected.tmp" > "keywords\selected.txt"
    del "keywords\selected.tmp"
    echo [KW] 已从 selected_keywords\*.txt 合并生成 keywords\selected.txt
  )
)

REM ===== 5.5) ★ 新增：关键词模块（放在 SEO 修复/补丁之后、sitemap 之前） =====
echo 🔤 正在执行关键词模块（build → enrich → select → inject）...

REM 全站去重词库（跨站共享）。如未设置则使用默认路径
if not defined NB_USED_GLOBAL set "NB_USED_GLOBAL=D:\project\used_keywords_global.txt"

REM 1/4 Build：从 Google Suggest 拉取 + 生成分类词表
if exist "%~dp0keywords_builder_google_only.py" (
  echo [KW] 1/4 build keywords...
  python "%~dp0keywords_builder_google_only.py"
  if errorlevel 1 echo [KW][WARN] builder failed（可继续）
) else (
  echo [KW][ERR] 缺少 keywords_builder_google_only.py
)

REM 2/4 Enrich（可选）：补充/清洗/扩展
if exist "%~dp0enrich_keywords.py" (
  echo [KW] 2/4 enrich keywords...
  python "%~dp0enrich_keywords.py"
  if errorlevel 1 echo [KW][WARN] enrich failed（可继续）
) else (
  echo [KW] 2/4 enrich 跳过（未找到 enrich_keywords.py）
)

REM 3/4 Select：跨站去重 + 为页面分配唯一长尾词
set "NB_USED_GLOBAL=%NB_USED_GLOBAL%"
if exist "%~dp0select_keywords.py" (
  echo [KW] 3/4 select & cross-site dedup...
  python "%~dp0select_keywords.py"
  if errorlevel 1 echo [KW][WARN] select failed（可继续）
) else (
  echo [KW][ERR] 缺少 select_keywords.py
)

REM 4/4 Inject：把长尾词注入到 <title>/<meta desc>/<h1>/<img alt>
if exist "%~dp0inject_keywords.py" (
  echo [KW] 4/4 inject into pages...
  if not exist ".nb_injected.flag" (
    python "%~dp0inject_keywords.py" --force
    if not errorlevel 1 (
      type nul > ".nb_injected.flag"
    ) else (
      echo [KW][WARN] inject 执行报错（已尝试 --force）
    )
  ) else (
    python "%~dp0inject_keywords.py"
    if errorlevel 1 echo [KW][WARN] inject 执行报错
  )
) else (
  echo [KW][ERR] 缺少 inject_keywords.py
)

REM ===== 5.6) ★ 固定映射 + 自动补正文段（100–180词），放在 inject 之后、sitemap 之前 =====
if exist "%~dp0kw_persist_and_fill.py" (
  echo 📝 固定关键词映射 + 自动补充正文...
  python "%~dp0kw_persist_and_fill.py" --root . --pool keywords\selected.txt --min-words 100 --max-words 180
) else (
  echo ⚠️ 未找到 kw_persist_and_fill.py，跳过。
)

REM ===== 6) 生成/重建正确的 sitemap.xml =====
echo 🗺️ 正在重建 sitemap.xml...
python "%~dp0sitemap_fix.py"

REM 强制把 sitemap.xml 纳入版本控制（防止被 .gitignore 忽略）
where git >nul 2>nul && (
  git rev-parse --is-inside-work-tree >nul 2>nul && (
    git add -f sitemap.xml >nul 2>nul
  )
)

REM ===== 7) 上传（你的原流程） =====
echo 🚀 正在上传到 GitHub 仓库...
python auto_git_push.py

REM ===== 8) 自动读取 domain 并 Ping 地图（带部署探测与重试） =====
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

REM 没有本地 sitemap 就不 Ping（理论上上一步已生成，这里只是兜底）
if not exist "%~dp0sitemap.xml" (
  echo ⚠️ 本地未发现 sitemap.xml，跳过 Ping。
  goto :END
)

REM 部署存在缓存/延迟：HEAD 探测 6 次（每次 10 秒）
powershell -NoProfile -Command ^
  "$u='%SITEMAP_URL%'; $ok=$false; for($i=1;$i -le 6;$i++){ try{ $r=Invoke-WebRequest -UseBasicParsing -Uri $u -Method Head -TimeoutSec 20; if($r.StatusCode -eq 200){$ok=$true; break} }catch{}; Start-Sleep -Seconds 10 }; if($ok){'OK'}" > "%~dp0logs\sitemap_probe.tmp"
set /p PROBE=<"%~dp0logs\sitemap_probe.tmp"
del "%~dp0logs\sitemap_probe.tmp" >nul 2>&1

if not "%PROBE%"=="OK" (
  echo ⚠️ 部署可能未完全就绪，先尝试 Ping（如 404，稍后可再补 Ping）。
)

REM 正式 Ping（Google + Bing），各重试 3 次
powershell -NoProfile -Command ^
  "$u='%SITEMAP_URL%'; $eps=@('https://www.google.com/ping?sitemap=','https://www.bing.com/ping?sitemap=');" ^
  "foreach($e in $eps){ for($i=1;$i -le 3; $i++){ try{ $r=Invoke-WebRequest -UseBasicParsing -Uri ($e + [uri]::EscapeDataString($u)) -TimeoutSec 20; Write-Host ('PING '+$e+' -> '+$r.StatusCode); if($r.StatusCode -eq 200){ break } } catch { Write-Host ('PING '+$e+' FAIL try'+$i+': '+$_.Exception.Message) } Start-Sleep -Seconds 5 } }"

echo ✅ 全部流程执行完毕！
:END
pause
endlocal
