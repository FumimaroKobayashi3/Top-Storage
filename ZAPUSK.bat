@echo off
title Запуск Хранилища ТОП (FastAPI + React)
echo   ЗАПУСК ХРАНИЛИЩА "ТОП"

python initdb.py
start cmd /k "cd Back && python -m uvicorn main:app --reload"

start cmd /k "cd Front && npm run dev"


echo Бэкенд API:  http://127.0.0.1:8000
echo Фронтенд UI: http://localhost:5173
