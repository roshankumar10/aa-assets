@echo off
rem Render intro/outro videos for chosen levels.
rem   Double-click            -> asks which levels and which parts
rem   render_levels.bat 1 3   -> renders intro + outro for levels 1 and 3, no questions
rem   render_levels.bat 1 3 --intros   (any make_all.py options work after the numbers)
setlocal EnableDelayedExpansion
title Render level videos
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python is not installed or not on PATH.
    pause
    exit /b 1
)

if not "%~1"=="" (
    set "ARGS=%*"
    goto :run
)

echo Levels available:
for %%f in (levels\level_*.json) do echo    %%~nf
echo.
set "LEVELS="
set /p "LEVELS=Which levels? Type numbers separated by spaces, e.g. 1 3 (just Enter = all): "

echo.
echo What should be rendered?
echo    1. Intro and outro
echo    2. Intro only
echo    3. Outro only
set "PART="
set /p "PART=Type 1, 2 or 3 and press Enter (just Enter = 1): "
set "PARTFLAG="
if "!PART!"=="2" set "PARTFLAG=--intros"
if "!PART!"=="3" set "PARTFLAG=--outros"

set "ARGS=!LEVELS! !PARTFLAG!"

echo.
echo About to run: python make_all.py !ARGS!
echo (existing videos for these levels will be replaced)
set "GO="
set /p "GO=Start? Type Y and press Enter: "
if /i not "!GO!"=="Y" (
    echo Cancelled. Nothing was rendered.
    pause
    exit /b 0
)

:run
echo.
python make_all.py !ARGS!
if errorlevel 1 (
    echo.
    echo Rendering stopped with an error - see the message above.
) else (
    echo.
    echo Done.
)
pause
