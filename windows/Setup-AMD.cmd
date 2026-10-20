@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0bootstrap.ps1" -Backend amd
if errorlevel 1 pause
