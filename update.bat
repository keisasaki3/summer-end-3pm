@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title 午後三時、夏の果。 Updater

echo.
echo ========================================
echo   午後三時、夏の果。 - One Click Update
echo ========================================
echo.

if not exist "update.zip" (
  echo [ERROR] update.zip was not found.
  echo Put update.zip in this folder and run update.bat again.
  pause
  exit /b 1
)

where powershell >nul 2>&1
if errorlevel 1 (
  echo [ERROR] PowerShell was not found.
  pause
  exit /b 1
)

if exist ".nantoka_update_tmp" rmdir /s /q ".nantoka_update_tmp"
mkdir ".nantoka_update_tmp"

echo [1/5] Extracting update.zip...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Expand-Archive -LiteralPath 'update.zip' -DestinationPath '.nantoka_update_tmp' -Force"
if errorlevel 1 goto :fail

echo [2/5] Removing obsolete files...
if exist ".nantoka_update_tmp\.nantoka-delete.txt" (
  for /f "usebackq delims=" %%F in (".nantoka_update_tmp\.nantoka-delete.txt") do (
    if not "%%F"=="" (
      if exist "%%F" del /f /q "%%F" >nul 2>&1
      if exist "%%F\" rmdir /s /q "%%F" >nul 2>&1
    )
  )
  del /f /q ".nantoka_update_tmp\.nantoka-delete.txt" >nul 2>&1
)

echo [3/5] Applying update...
xcopy ".nantoka_update_tmp\*" "." /E /Y /I /Q >nul
if errorlevel 1 goto :fail

rmdir /s /q ".nantoka_update_tmp"

echo [4/5] Building...
call npm run build
if errorlevel 1 goto :fail

echo [5/5] Starting server...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":8080" ^| findstr "LISTENING"') do (
  taskkill /PID %%P /F >nul 2>&1
)
start "午後三時、夏の果。 Server" cmd /k "cd /d ""%~dp0"" && npm start"

echo.
echo ========================================
echo   Update complete.
echo ========================================
echo.
echo You can close this updater window.
timeout /t 3 >nul
exit /b 0

:fail
echo.
echo [ERROR] Update failed.
echo Check the message above. Your project folder has not been deleted.
if exist ".nantoka_update_tmp" rmdir /s /q ".nantoka_update_tmp"
pause
exit /b 1
