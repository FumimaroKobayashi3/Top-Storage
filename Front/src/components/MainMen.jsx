import { useEffect, useState } from "react"

export default function MainMen({ SetScreen }) {
    const [stats, setStats] = useState({
        used_bytes: 0,
        limit_bytes: 5368709120, // 5 ГБ по дефолту
        total_files: 0,
        trash_files: 0
    })

    function loadStats() {
        fetch('/api/stats')
            .then(res => res.json())
            .then(data => setStats(data))
            .catch(err => console.log("Косяк при фетче статистики:", err))
    }

    useEffect(() => {
        loadStats()
    }, [])

    // Перевод байтов в гигабайты
    const usedBytes = stats.used_bytes || 0
    const limitBytes = stats.limit_bytes || 5368709120

    const usedGB = (usedBytes / 1073741824).toFixed(2)
    const limitGB = (limitBytes / 1073741824).toFixed(0)

    return (
        <div className="main-menu-container">
            <h2>Дашборд Хранилища «ТОП»</h2>
            <p>Панель управления файловым пространством</p>

            <hr />

            <div className="dashboard-grid">
                <div className="stat-card">
                    <h4>Занятое место</h4>
                    <p>{usedGB} ГБ из {limitGB} ГБ</p>
                    <progress value={usedBytes} max={limitBytes} className="progress-bar-container" />
                </div>

                <div className="stat-card">
                    <h4>Активных файлов</h4>
                    <p>{stats.total_files || 0} шт.</p>
                    <button onClick={() => SetScreen("FileManager")}>Открыть диск</button>
                </div>

                <div className="stat-card">
                    <h4>Файлов в корзине</h4>
                    <p className="badge-blocked">{stats.trash_files || 0} шт.</p>
                    <button onClick={() => SetScreen("TrashBin")}>Открыть корзину</button>
                </div>
            </div>
        </div>
    )
}