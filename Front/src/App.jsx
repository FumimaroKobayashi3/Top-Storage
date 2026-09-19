import { useState } from "react"
import SideBar from "./components/SideBar.jsx"
import MainMen from "./components/MainMen.jsx"
import FileManager from "./components/FileManager.jsx"
import TrashBin from "./components/TrashBin.jsx"
import Options from "./components/Options.jsx"
import Auth from "./components/Auth.jsx"
import "./components/themes.css"

export default function App() {
    const [screen, setScreen] = useState("Menu")

    // Состояние темы (по умолчанию Темная)
    const [theme, setTheme] = useState("theme-dark")
    const [User, SetUser] = useState(() => {
        const saved = localStorage.getItem("top_user")
        if (saved) {
            return JSON.parse(saved)
        }
        return null
    })

    // Функция переключения темы
    function switchTheme() {
        if (theme === "theme-dark") {
            setTheme("theme-light")
        } else {
            setTheme("theme-dark")
        }
    }
    function handleLogout() {
        localStorage.removeItem("top_user")
        SetUser(null)
        setScreen("Menu")
    }
    //если юзер не залогинут он за пределы окна не выйдет
    if (!User) {
        return (
            <div className={`app-container ${theme}`}>
                <Auth onLogin={userData => SetUser(userData)} />
            </div>
        )
    }
    // если он залогинен
    function renderScreen() {
        if (screen === "FileManager") {
            return <FileManager SetScreen={setScreen} User={User} />
        }
        if (screen === "TrashBin") {
            return <TrashBin SetScreen={setScreen} User={User} />
        }
        if (screen === "Options") {
            return (
                <Options 
                    SetScreen={setScreen} 
                    themes={theme} 
                    switchTheme={switchTheme} 
                    User={User} 
                    onLogout={handleLogout} 
                />
            )
        }
        return <MainMen SetScreen={setScreen} />
    }

    return (
        <div className={`app-container ${theme}`}>
            <header className="app-header">
                <h2>Веб-файлохранилище «ТОП»</h2>
                <div>
                    <span>Юзер: <b>{User.username}</b> | </span>
                    <span>Режим: {theme === "theme-dark" ? "Тёмная тема" : "Светлая тема"}</span>
                </div>
            </header>

            <div className="app-layout">
                <SideBar SetScreen={setScreen} />

                <main className="main-content">
                    {renderScreen()}
                </main>
            </div>
        </div>
    )
}