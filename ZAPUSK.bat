@echo off
title Хранилище «ТОП»
chcp 65001 > nul

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

echo [1/3] Проверка бэкенда Python...
cd Back

if not exist "venv" (
    echo Создание свежего venv...
    python -m venv venv
)

echo Установка/обновление зависимостей...
call venv\Scripts\activate.bat
python -m pip install -r requirements.txt

echo Инициализация базы данных...
python InitDB.py
cd ..

echo [2/3] Проверка фронтенда React...
cd Front
if not exist "node_modules" (
    echo Установка модулей Node.js...
    call npm install
)
cd ..

echo [3/3] Запуск сервисов...
start "Backend_TOP" cmd /k "cd /d "%ROOT_DIR%Back" && call venv\Scripts\activate.bat && python -m uvicorn main:app --reload --port 8000"
start "Frontend_TOP" cmd /k "cd /d "%ROOT_DIR%Front" && npm run dev"

echo =========================================
echo  Система «ТОП» успешно запущена!
echo  Бэкенд:  http://127.0.0.1:8000
echo  Фронтенд: http://localhost:5173
echo =========================================