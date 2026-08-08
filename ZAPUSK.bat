@echo off
title Запуск Хранилища ТОП (через Docker)
echo ЗАПУСК КОНТЕЙНЕРОВ DOCKER...
chcp 65001 > nul
docker compose up --build

pause