import { useEffect, useState } from "react"

export default function MainMen({ SetScreen }) {
    const [stats, setStats] = useState({
        used_bytes: 0,
        limit_bytes: 42949672960,
        total_files: 0,
        blocked_viruses: 0
    })

    function loadStats() {
        fetch('http://127.0.0.1:8000/api/stats')
            .then(res => res.json())
            .then(data => setStats(data))
            .catch(err => console.log("Косяк при фетче статистики:", err))
    }

    useEffect(() => {
        loadStats()
    }, [])

    // Перевод байтов в гигабайты
    const usedBytes = stats.used_bytes || 0
    const limitBytes = stats.limit_bytes || 42949672960

    const usedGB = (usedBytes / 1073741824).toFixed(2)
    const limitGB = (limitBytes / 1073741824).toFixed(0)

    return (
        <div className="main-menu-container">
            <h2>📊 Дашборд Хранилища «ТОП»</h2>
            <p>Система защиты и контроля файлового пространства</p>

            <hr />

            <div className="dashboard-grid">
                <div className="stat-card">
                    <h4>💾 Занятое место</h4>
                    <p>{usedGB} ГБ из {limitGB} ГБ</p>
                    <progress value={usedBytes} max={limitBytes} className="progress-bar-container" />
                </div>

                <div className="stat-card">
                    <h4>📁 Активных файлов</h4>
                    <p>{stats.total_files || 0} шт.</p>
                    <button onClick={() => SetScreen("FileManager")}>Открыть диск</button>
                </div>

                <div className="stat-card">
                    <h4>🛡️ Заблокировано угроз</h4>
                    <p className="badge-blocked">{stats.blocked_viruses || 0} угроз</p>
                    <button onClick={() => SetScreen("TrashBin")}>Проверить корзину</button>
                </div>
            </div>
        </div>
    )
}