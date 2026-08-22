@echo off
title Хранилище ТОП (FastAPI + ReactJS)

echo Запуск инициализации базы данных...
cd Back
python InitDB.py
cd ..

echo Запуск Бэкенда FastAPI...
start cmd /k "cd Back && uvicorn main:app --reload --port 8000"

echo Запуск Фронтенда Vite...
start cmd /k "cd Front && npm run dev"

echo Проект успешно запущен!