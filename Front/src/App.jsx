import { useState } from "react"
import SideBar from "./components/SideBar.jsx"
import MainMen from "./components/MainMen.jsx"
import FileManager from "./components/FileManager.jsx"
import TrashBin from "./components/TrashBin.jsx"
import Options from "./components/Options.jsx"
import "./components/themes.css"

export default function App() {
    const [screen, setScreen] = useState("Menu")

    // Состояние темы (по умолчанию Темная)
    const [theme, setTheme] = useState("theme-dark")

    // Функция переключения темы
    function switchTheme() {
        if (theme === "theme-dark") {
            setTheme("theme-light")
        } else {
            setTheme("theme-dark")
        }
    }

    // Простая функция выбора экрана 
    function renderScreen() {
        if (screen === "FileManager") {
            return <FileManager SetScreen={setScreen} />
        }
        if (screen === "TrashBin") {
            return <TrashBin SetScreen={setScreen} />
        }
        if (screen === "Options") {
            return <Options SetScreen={setScreen} themes={theme} switchTheme={switchTheme} />
        }
        return <MainMen SetScreen={setScreen} />
    }

    return (
        <div className={`app-container ${theme}`}>
            <header className="app-header">
                <h2>Веб-файлохранилище «ТОП»</h2>
                <span>Режим: {theme === "theme-dark" ? "Тёмная тема" : "Светлая тема"}</span>
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