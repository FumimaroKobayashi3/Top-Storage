import { useState } from "react"

export default function Auth({ onLogin }) {
    const [isRegister, setIsRegister] = useState(false)
    const [username, setUsername] = useState("")
    const [password, setPassword] = useState("")
    const [statusText, setStatusText] = useState("")

    function handleAuth(e) {
        e.preventDefault()
        setStatusText("")

        if (!username || !password) {
            setStatusText("Введите логин и пароль")
            return
        }

        const url = isRegister ? "/api/signup" : "/api/login"

        fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        })
            .then(res => res.json())
            .then(data => {
                if (data.status === "ok") {
                    if (isRegister) {
                        setStatusText("Успешно! Теперь войдите")
                        setIsRegister(false)
                        setPassword("")
                    } else {
                        localStorage.setItem("top_user", JSON.stringify(data))
                        onLogin(data)
                    }
                } else {
                    // Если бэк вернул ошибку или detail от FastAPI
                    setStatusText(data.message || data.detail || "Ошибка входа")
                }
            })
            .catch(() => setStatusText("Сервер недоступен"))
    }

    return (
        <div className="auth-box">
            <h3>{isRegister ? "Регистрация" : "Вход в систему"}</h3>
            <p>Хранилище «ТОП»</p>
            <hr />

            <form onSubmit={handleAuth} className="auth-form">
                <input
                    type="text"
                    placeholder="Логин"
                    value={username}
                    onChange={e => setUsername(e.target.value)}
                />
                <input
                    type="password"
                    placeholder="Пароль"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                />

                {statusText && <p className="badge-blocked">{statusText}</p>}

                <button type="submit">
                    {isRegister ? "Зарегистрироваться" : "Войти"}
                </button>
            </form>

            <hr />
            <button 
                type="button" 
                onClick={() => { setIsRegister(!isRegister); setStatusText(""); }}
            >
                {isRegister ? "Уже есть аккаунт? Войти" : "Создать аккаунт"}
            </button>
        </div>
    )
}