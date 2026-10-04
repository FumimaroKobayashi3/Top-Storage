import { useEffect, useState } from "react"

export default function MainMen({ SetScreen, User }) {
    // 5 ГБ в байтах (5 * 1024 * 1024 * 1024)
    const [stats, setStats] = useState({
        used_bytes: 0,
        limit_bytes: 5 * 1024 * 1024 * 1024,
        total_files: 0,
        trash_files: 0
    })

    function loadStats() {
        const uid = User ? User.user_id : 1
        fetch(`/api/stats?user_id=${uid}`)
            .then(res => res.json())
            .then(data => setStats(data))
            .catch(err => console.log("Косяк при фетче статистики:", err))
    }

    useEffect(() => {
        loadStats()
    }, [])

    const bytesInGb = 1024 * 1024 * 1024
    const usedGB = (stats.used_bytes / bytesInGb).toFixed(2)
    const limitGB = (stats.limit_bytes / bytesInGb).toFixed(0)

    return (
        <div className="main-menu-container">
            <h2>Дашборд Хранилища «ТОП»</h2>
            <p>Панель управления файловым пространством</p>

            <hr />

            <div className="dashboard-grid">
                <div className="stat-card">
                    <h4>Занятое место</h4>
                    <p>{usedGB} ГБ из {limitGB} ГБ</p>
                    <progress 
                        value={stats.used_bytes} 
                        max={stats.limit_bytes} 
                        className="progress-bar-container" 
                    />
                </div>

                <div className="stat-card">
                    <h4>Активных файлов</h4>
                    <p>{stats.total_files} шт.</p>
                    <button onClick={() => SetScreen("FileManager")}>Открыть диск</button>
                </div>

                <div className="stat-card">
                    <h4>Файлов в корзине</h4>
                    <p className="badge-blocked">{stats.trash_files} шт.</p>
                    <button onClick={() => SetScreen("TrashBin")}>Открыть корзину</button>
                </div>
            </div>
        </div>
    )
}