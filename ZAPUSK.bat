@echo off
title Хранилище «ТОП»
chcp 65001 > nul

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

echo ===================================================
echo   Запуск файлового хранилища «ТОП»
echo ===================================================

if not exist "Front\dist" (
    echo [ОШИБКА] Не найдена папка Front\dist!
    pause
    exit /b 1
)

cd Back

:: Проверяем наличие venv или системного Python
if exist "venv\Scripts\python.exe" (
    set "PY=venv\Scripts\python.exe"
) else (
    set "PY=python"
)

:: Запуск базы и сервера на локальном адресе 127.0.0.1
"%PY%" InitDB.py >nul 2>nul
start "Storage_TOP_Backend" "%PY%" -m uvicorn main:app --host 127.0.0.1 --port 8000

:: Пауза 2 секунды на запуск сокета и открытие сайта в браузере
timeout /t 2 > nul
start http://127.0.0.1:8000

echo Сервер работает на http://127.0.0.1:8000
echo Черное окно сервера не закрывай до конца показа.