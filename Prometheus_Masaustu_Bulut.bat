@echo off
chcp 65001 >nul
setlocal
title PROMETHEUS AI // Bulut Masaustu Penceresi

set "URL=https://prometheus-ai-taupe.vercel.app"
set "APP_BIN="

for %%B in (
    "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
    "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
    "%ProgramFiles%\Google\Chrome\Application\chrome.exe"
    "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
    "%LocalAppData%\Google\Chrome\Application\chrome.exe"
) do (
    if exist "%%~B" (
        set "APP_BIN=%%~B"
        goto :launch
    )
)

:launch
if not "%APP_BIN%"=="" (
    start "" "%APP_BIN%" --app=%URL% --window-size=1360,860
) else (
    start "" "%URL%"
)
