export default function SideBar({ SetScreen }){
    return (
        <div className="sidebar-dock">
            <h4>Хранилище ТОП</h4>
            
            <div className="sidebar-actions">
                <button onClick={() => SetScreen("Menu")}>◁ Дашборд</button>
                <button onClick={() => SetScreen("FileManager")}>▶ Мой Диск</button>
                <button onClick={() => SetScreen("TrashBin")}>♻ Корзина</button>
                <button onClick={() => SetScreen("Options")}>⚙ Настройки</button>
            </div>
        </div>
    )
}