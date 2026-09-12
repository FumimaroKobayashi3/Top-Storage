import { useState } from "react"

export default function Options({ SetScreen, themes, switchTheme }) {
    const [dbStat, setDbStat] = useState("Не проверено")
    const [logs, setLogs] = useState([])
    const [showLogs, setShowLogs] = useState(false)

    function checkStatus() {
        fetch('/api/stats')
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

    // Загрузка логов из бэкенда
    function loadSystemLogs() {
        fetch('/api/logs')
            .then(res => res.json())
            .then(data => {
                setLogs(data)
                setShowLogs(true)
            })
            .catch(err => console.log("Ошибка загрузки логов:", err))
    }

    // Вынос логики строк таблицы логов
    let logsRowsElement = null
    if (logs.length === 0) {
        logsRowsElement = (
            <tr>
                <td colSpan="4">Записей в логах пока нет</td>
            </tr>
        )
    } else {
        logsRowsElement = logs.map(log => (
            <tr key={log.LogId}>
                <td>{log.EventType}</td>
                <td>{log.FileName}</td>
                <td>{log.ScanResult}</td>
                <td>{log.Timestamp}</td>
            </tr>
        ))
    }

    // Отображение таблицы логов
    let logsTableElement = null
    if (showLogs === true) {
        logsTableElement = (
            <table className="storage-table">
                <thead>
                    <tr>
                        <th>Событие</th>
                        <th>Имя файла</th>
                        <th>Статус операции</th>
                        <th>Дата</th>
                    </tr>
                </thead>
                <tbody>
                    {logsRowsElement}
                </tbody>
            </table>
        )
    }

    return (
        <div className="options-window">
            <div className="options-header">
                <button onClick={() => SetScreen("Menu")}>◁ Меню</button>
                <h2>Настройки системы «ТОП»</h2>
            </div>

            <hr />

            {/* Смена темы */}
            <div className="options-section">
                <h3>Оформление</h3>
                <p>Текущая тема: {themes}</p>
                <button onClick={switchTheme}>Сменить тему ☀/☽</button>
            </div>

            <hr />

            {/* Диагностика бэкенда */}
            <div className="options-section">
                <h3>Диагностика сервера</h3>
                <p>Статус связи: {dbStat}</p>
                <button onClick={checkStatus}>Проверить связь с FastAPI</button>
            </div>

            <hr />

            {/* Системный журнал операций */}
            <div className="options-section">
                <h3>Системный журнал событий</h3>
                <button onClick={loadSystemLogs}>Показать журнал событий</button>
                {logsTableElement}
            </div>

            <hr />

            {/* Информационный блок */}
            <div className="options-section">
                <h3>Параметры окружения</h3>
                <p>Лимит диска: 5 ГБ</p>
            </div>
        </div>
    )
}