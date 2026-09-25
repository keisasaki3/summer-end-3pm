@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Publish 午後三時、夏の果。 to GitHub

echo.
echo ========================================
echo   午後三時、夏の果。 - GitHub Publish
echo   keisasaki3/summer-end-3pm
echo ========================================
echo.

where git >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Git was not found.
  echo Install Git for Windows, then run this file again.
  pause
  exit /b 1
)

if not exist ".git" (
  git init
  if errorlevel 1 goto :fail
)

git config user.name "keisasaki3"
git config user.email "61055342+keisasaki3@users.noreply.github.com"

git remote get-url origin >nul 2>&1
if errorlevel 1 (
  git remote add origin "https://github.com/keisasaki3/summer-end-3pm.git"
) else (
  git remote set-url origin "https://github.com/keisasaki3/summer-end-3pm.git"
)

git add -A
if errorlevel 1 goto :fail

git diff --cached --quiet
if errorlevel 1 (
  git commit -m "Refactor game name to 午後三時、夏の果。"
  if errorlevel 1 goto :fail
) else (
  echo [INFO] No new local changes to commit.
)

git branch -M main
if errorlevel 1 goto :fail
git push -u origin main
if errorlevel 1 goto :fail

echo.
echo Publish complete.
pause
exit /b 0

:fail
echo.
echo [ERROR] GitHub publish failed.
pause
exit /b 1
