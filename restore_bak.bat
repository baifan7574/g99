@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

echo === 用 .bak 覆盖恢复 .html / .htm（会保存 .broken 备份） ===
echo 目录：%cd%
echo.

REM 1) 先处理 .html.bak
for /r %%F in (*.html.bak) do (
  set "BAK=%%~fF"
  set "ORIG=%%~dpnF"        REM 例如 D:\site\page.html
  if exist "!ORIG!" (
    echo 备份坏文件 -> "!ORIG!.broken"
    move /y "!ORIG!" "!ORIG!.broken" >nul
  )
  echo 覆盖恢复: "!BAK!" -> "!ORIG!"
  copy /y "!BAK!" "!ORIG!" >nul
)

REM 2) 再处理 .htm.bak
for /r %%F in (*.htm.bak) do (
  set "BAK=%%~fF"
  set "ORIG=%%~dpnF"        REM 例如 D:\site\page.htm
  if exist "!ORIG!" (
    echo 备份坏文件 -> "!ORIG!.broken"
    move /y "!ORIG!" "!ORIG!.broken" >nul
  )
  echo 覆盖恢复: "!BAK!" -> "!ORIG!"
  copy /y "!BAK!" "!ORIG!" >nul
)

echo.
echo ✅ 完成：已用 .bak 覆盖恢复（坏页面已另存為 .broken）
pause
endlocal
