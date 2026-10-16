@echo off
rem Double-click to install (or update) and start the library system.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install.ps1" %*
