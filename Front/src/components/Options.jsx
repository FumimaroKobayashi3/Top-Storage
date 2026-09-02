import { useState } from "react"

export default function Options({ SetScreen, themes, switchTheme }){

    const [dbStat, setDbStat] = useState("Не проверено")
    const [logs, setLogs] = useState([])
    const [showLogs, setShowLogs] = useState(false)

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

    // Загрузка логов из бэкенда
    function loadSecurityLogs() {
        fetch('http://127.0.0.1:8000/api/logs')
        .then(res => res.json())
        .then(data => {
            setLogs(data)
            setShowLogs(true)
        })
        .catch(err => console.log("Ошибка загрузки логов:", err))
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

            {/* Журнал безопасности VirusTotal */}
            <div className="options-section">
                <h3>Журнал безопасности (VirusTotal)</h3>
                <button onClick={loadSecurityLogs}>🛡️ Показать журнал проверок</button>
                
                {showLogs ? (
                    <table className="storage-table">
                        <thead>
                            <tr>
                                <th>Событие</th>
                                <th>Имя файла</th>
                                <th>Результат сканирования</th>
                                <th>Дата</th>
                            </tr>
                        </thead>
                        <tbody>
                            {logs.length === 0 ? (
                                <tr>
                                    <td colSpan="4">Записей в логах пока нет</td>
                                </tr>
                            ) : (
                                logs.map(log => (
                                    <tr key={log.LogId}>
                                        <td>{log.EventType}</td>
                                        <td>{log.FileName}</td>
                                        <td>{log.ScanResult}</td>
                                        <td>{log.Timestamp}</td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                ) : null}
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