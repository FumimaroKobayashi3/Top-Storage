import { useState, useEffect } from "react"

export default function FileManager({ SetScreen }) {
    const [filesList, setFilesList] = useState([])
    const [selectedCategory, setSelectedCategory] = useState("ALL")
    const [previewFile, setPreviewFile] = useState(null)
    const [previewTextContent, setPreviewTextContent] = useState("")
    const [uploadStatus, setUploadStatus] = useState("")
    
    // Состояния для шеринга сгорающих ссылок
    const [shareFileId, setShareFileId] = useState(null)
    const [shareHours, setShareHours] = useState(72)
    const [generatedLink, setGeneratedLink] = useState("")

    function loadFiles() {
        fetch('http://127.0.0.1:8000/api/files')
            .then(res => res.json())
            .then(data => setFilesList(data))
            .catch(err => console.log("Ошибка загрузки файлов:", err))
    }

    useEffect(() => {
        loadFiles()
    }, [])

    function handleFileUpload(e) {
        const file = e.target.files[0]
        if (file) {
            setUploadStatus("Проверка на вирусы и загрузка...")
            const formData = new FormData()
            formData.append("file", file)

            fetch('http://127.0.0.1:8000/api/upload', {
                method: 'POST',
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                setUploadStatus(data.message)
                loadFiles()
            })
            .catch(() => setUploadStatus("Ошибка загрузки"))
        }
    }

    function moveToTrash(id) {
        fetch(`http://127.0.0.1:8000/api/trash/move/${id}`, { method: 'POST' })
            .then(() => {
                setPreviewFile(null)
                setShareFileId(null)
                loadFiles()
            })
    }

    function openPreview(file) {
        setPreviewFile(file)
        setPreviewTextContent("")

        if (file.FileType.includes("text")) {
            fetch(`http://127.0.0.1:8000/api/download/${file.FileID}`)
                .then(res => res.text())
                .then(txt => setPreviewTextContent(txt))
        }
    }

    function generateShareLink(fileId) {
        fetch(`http://127.0.0.1:8000/api/files/share/${fileId}?hours=${shareHours}`, {
            method: 'POST'
        })
        .then(res => res.json())
        .then(data => {
            if (data.public_url) {
                setGeneratedLink(data.public_url)
            }
        })
        .catch(err => console.log("Ошибка создания ссылки:", err))
    }

    function openShareBox(fileId) {
        setShareFileId(fileId)
        setGeneratedLink("")
        setShareHours(72)
    }

    // Фильтрация файлов по категориям
    const filteredFiles = filesList.filter(file => {
        if (selectedCategory === "IMAGES") {
            return file.FileType.includes("image")
        }
        if (selectedCategory === "DOCS") {
            return file.FileType.includes("pdf") || file.FileType.includes("document")
        }
        if (selectedCategory === "TEXT") {
            return file.FileType.includes("text")
        }
        if (selectedCategory === "VIDEO") {
            return file.FileType.includes("video") || file.Filename.endsWith(".mp4") || file.Filename.endsWith(".avi")
        }
        if (selectedCategory === "AUDIO") {
            return file.FileType.includes("audio") || file.Filename.endsWith(".mp3") || file.Filename.endsWith(".wav") || file.Filename.endsWith(".m4a")
        }
        return true
    })

    return (
        <div className="file-manager-container">
            <h3>📂 Мой Диск</h3>

            <div className="upload-section">
                <label>Загрузить файл: </label>
                <input type="file" onChange={handleFileUpload} />
                {uploadStatus ? <p>{uploadStatus}</p> : null}
            </div>

            <hr />

            {/* Фильтр по категориям */}
            <div className="category-tree">
                <b>Категории: </b>
                <button onClick={() => setSelectedCategory("ALL")}>Все ({filesList.length})</button>
                <button onClick={() => setSelectedCategory("IMAGES")}>Изображения</button>
                <button onClick={() => setSelectedCategory("DOCS")}>Документы PDF</button>
                <button onClick={() => setSelectedCategory("TEXT")}>Текстовые</button>
                <button onClick={() => setSelectedCategory("VIDEO")}>Видео (MP4/AVI)</button>
                <button onClick={() => setSelectedCategory("AUDIO")}>Аудио (MP3/WAV/M4A)</button>
            </div>

            <table className="storage-table">
                <thead>
                    <tr>
                        <th>Имя файла</th>
                        <th>Тип</th>
                        <th>Размер (байт)</th>
                        <th>Действия</th>
                    </tr>
                </thead>
                <tbody>
                    {filteredFiles.length === 0 ? (
                        <tr>
                            <td colSpan="4">Файлы не найдены</td>
                        </tr>
                    ) : (
                        filteredFiles.map(file => (
                            <tr key={file.FileID}>
                                <td>{file.Filename}</td>
                                <td>{file.FileType}</td>
                                <td>{file.FileSize}</td>
                                <td>
                                    <button onClick={() => openPreview(file)}>👁️ Предпросмотр</button>
                                    <a href={`http://127.0.0.1:8000/api/download/${file.FileID}`} download>
                                        <button>💾 Скачать</button>
                                    </a>
                                    <button onClick={() => openShareBox(file.FileID)}>🔗 Поделиться</button>
                                    <button onClick={() => moveToTrash(file.FileID)} className="danger-button">🗑️ В корзину</button>
                                </td>
                            </tr>
                        ))
                    )}
                </tbody>
            </table>

            {/* Окно генерации сгорающей ссылки */}
            {shareFileId ? (
                <div className="preview-box">
                    <hr />
                    <h4>🔗 Публичный доступ (Сгорающая ссылка)</h4>
                    
                    <label>Срок жизни ссылки: </label>
                    <select value={shareHours} onChange={(e) => setShareHours(Number(e.target.value))}>
                        <option value={2}>2 часа</option>
                        <option value={5}>5 часов</option>
                        <option value={24}>24 часа (1 день)</option>
                        <option value={72}>72 часа (3 дня)</option>
                        <option value={0}>Не удалять (вечная)</option>
                    </select>
                    
                    <br /><br />
                    <button onClick={() => generateShareLink(shareFileId)}>Сгенерировать ссылку</button>

                    {generatedLink ? (
                        <div>
                            <br />
                            <p><b>Готовая ссылка для скачивания:</b></p>
                            <input type="text" value={generatedLink} readOnly />
                        </div>
                    ) : null}

                    <br /><br />
                    <button onClick={() => setShareFileId(null)}>✘ Закрыть</button>
                </div>
            ) : null}

            {/* Окно предпросмотра выбранного файла */}
            {previewFile ? (
                <div className="preview-box">
                    <hr />
                    <h4>Просмотр: {previewFile.Filename}</h4>

                    {previewFile.FileType.includes("image") ? (
                        <img 
                            src={`http://127.0.0.1:8000/api/download/${previewFile.FileID}`} 
                            alt="Превью" 
                            className="file-preview-img" 
                        />
                    ) : null}

                    {previewFile.FileType.includes("text") ? (
                        <textarea value={previewTextContent} readOnly rows={8} className="file-text-area" />
                    ) : null}

                    {previewFile.FileType.includes("pdf") || previewFile.Filename.endsWith(".pdf") ? (
                        <iframe 
                            src={`http://127.0.0.1:8000/api/download/${previewFile.FileID}`} 
                            title="PDF Preview" 
                            className="file-preview-pdf"
                        />
                    ) : null}

                    {previewFile.FileType.includes("video") || previewFile.Filename.endsWith(".mp4") || previewFile.Filename.endsWith(".avi") ? (
                        <video controls className="file-preview-video">
                            <source src={`http://127.0.0.1:8000/api/download/${previewFile.FileID}`} />
                        </video>
                    ) : null}

                    {previewFile.FileType.includes("audio") || previewFile.Filename.endsWith(".mp3") || previewFile.Filename.endsWith(".wav") || previewFile.Filename.endsWith(".m4a") ? (
                        <audio controls className="file-preview-audio">
                            <source src={`http://127.0.0.1:8000/api/download/${previewFile.FileID}`} />
                        </audio>
                    ) : null}

                    <br />
                    <button onClick={() => setPreviewFile(null)}>✘ Закрыть предпросмотр</button>
                </div>
            ) : null}
        </div>
    )
}