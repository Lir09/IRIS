@echo off
setlocal
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
  echo [error] venv\Scripts\python.exe not found
  echo Create venv and install dependencies first.
  exit /b 1
)

venv\Scripts\python.exe cli_client.py
