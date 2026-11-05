@echo off
where python >nul 2>nul
if errorlevel 1 (set "PY=py -3") else (set "PY=python")
%PY% "%~dp0build_release.py"
echo.
pause
