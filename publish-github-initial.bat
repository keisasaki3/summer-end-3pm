@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Publish 午後三時、夏の果 to GitHub

echo.
echo ========================================
echo   GitHub Initial Publish
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

if not exist ".gitignore" (
  >".gitignore" (
    echo node_modules/
    echo dist/
    echo .nantoka_update_tmp/
    echo update.zip
    echo *.log
    echo .env
  )
)

if not exist ".git" (
  git init
  if errorlevel 1 goto :fail
)

rem Local-only author identity for this repository.
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
  git commit -m "Publish beta 0.47"
  if errorlevel 1 goto :fail
) else (
  echo [INFO] No new local changes to commit.
)

git branch -M main
if errorlevel 1 goto :fail

echo.
echo Pushing the complete project to GitHub...
echo A GitHub sign-in window may open the first time.
echo.

rem Safe for this initial publish because the remote repository was verified
rem to contain only the auto-created README commit.
git push -u origin main --force
if errorlevel 1 goto :fail

echo.
echo ========================================
echo   Publish complete.
echo   https://github.com/keisasaki3/summer-end-3pm
echo ========================================
echo.
pause
exit /b 0

:fail
echo.
echo [ERROR] GitHub publish failed.
echo Read the Git error above. No local project files were deleted.
echo.
pause
exit /b 1
