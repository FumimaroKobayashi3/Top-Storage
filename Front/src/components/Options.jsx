import { useState } from "react"

export default function Options({ SetScreen, themes, switchTheme }){

    const [dbStat, setDbStat] = useState("Не проверено")

    function checkStatus(){
        fetch('http://127.0.0.1:8000/api/stats')
        .then(res => {
            if (res.ok) {
                setDbStat('Онлайн (FastAPI работает)')
            } else {
                setDbStat('Ошибка сервера')
            }
        })
        .catch(() => {
            setDbStat('Ошибка: оффлайн')
        })
    }

    return (
        <div className="options-window">
           
            <div className="options-header">
                <button onClick={() => SetScreen("Menu")}>◁ Меню</button>
                <h2>Настройки системы «ТОП»</h2>
            </div>

            <hr />

            {/* Смена темки*/}
            <div className="options-section">
                <h3>Оформление</h3>
                <p>Текущая тема: {themes}</p>
                <button onClick={switchTheme}>Сменить тему ☀/☽</button>
            </div>

            <hr />

            {/* Диагностика бэкенда  чтобы все было отлично*/}
            <div className="options-section">
                <h3>Диагностика сервера</h3>
                <p>Статус связи: {dbStat}</p>
                <button onClick={checkStatus}>Проверить связь с FastAPI</button>
            </div>

            <hr />

            {/* Информационный блок */}
            <div className="options-section">
                <h3>Безопасность и лимиты</h3>
                <p>Лимит диска: 40 ГБ (42 949 672 960 байт)</p>
                <p>Фильтрация: VirusTotal API (Порог блокировки: ≥20 угроз)</p>
            </div>

        </div>
    )
}