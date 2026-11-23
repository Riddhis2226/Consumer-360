@echo off
setlocal
REM Portable CMD wrapper for upload_to_postgres.ps1
REM Place both files in the Consumer-360 project root (or scripts\) and run:
REM   upload_to_postgres.bat
REM   upload_to_postgres.bat -Target supabase
REM   upload_to_postgres.bat -Target local -Mode append

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0upload_to_postgres.ps1" %*
exit /b %ERRORLEVEL%
