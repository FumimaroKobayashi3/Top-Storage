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
        fetch('/api/files')
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

            fetch('/api/upload', {
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
        fetch(`/api/trash/move/${id}`, { method: 'POST' })
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
            fetch(`/api/download/${file.FileID}`)
                .then(res => res.text())
                .then(txt => setPreviewTextContent(txt))
        }
    }

    function generateShareLink(fileId) {
        fetch(`/api/files/share/${fileId}?hours=${shareHours}`, {
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

    // Подготовка отображения статуса загрузки
    let uploadStatusElement = null
    if (uploadStatus !== "") {
        uploadStatusElement = <p>{uploadStatus}</p>
    }

    // Подготовка строк таблицы (Замена тернарника)
    let tableRowsElement = null
    if (filteredFiles.length === 0) {
        tableRowsElement = (
            <tr>
                <td colSpan="4">Файлы не найдены</td>
            </tr>
        )
    } else {
        tableRowsElement = filteredFiles.map(file => (
            <tr key={file.FileID}>
                <td>{file.Filename}</td>
                <td>{file.FileType}</td>
                <td>{file.FileSize}</td>
                <td>
                    <button onClick={() => openPreview(file)}>Предпросмотр</button>
                    <a href={`/api/download/${file.FileID}`} download>
                        <button>Скачать</button>
                    </a>
                    <button onClick={() => openShareBox(file.FileID)}>Поделиться</button>
                    <button onClick={() => moveToTrash(file.FileID)} className="danger-button">В корзину</button>
                </td>
            </tr>
        ))
    }

    // Подготовка окна сгорающей ссылки
    let shareBoxElement = null
    if (shareFileId !== null) {
        let generatedLinkElement = null
        if (generatedLink !== "") {
            generatedLinkElement = (
                <div>
                    <br />
                    <p><b>Готовая ссылка для скачивания:</b></p>
                    <input type="text" value={generatedLink} readOnly />
                </div>
            )
        }

        shareBoxElement = (
            <div className="preview-box">
                <hr />
                <h4>Публичный доступ (Сгорающая ссылка)</h4>
                
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

                {generatedLinkElement}

                <br /><br />
                <button onClick={() => setShareFileId(null)}>✘ Закрыть</button>
            </div>
        )
    }

    // Подготовка окна предпросмотра файлов
    let previewBoxElement = null
    if (previewFile !== null) {
        let mediaElement = null

        if (previewFile.FileType.includes("image")) {
            mediaElement = (
                <img 
                    src={`/api/download/${previewFile.FileID}`} 
                    alt="Превью" 
                    className="file-preview-img" 
                />
            )
        } else if (previewFile.FileType.includes("text")) {
            mediaElement = (
                <textarea value={previewTextContent} readOnly rows={8} className="file-text-area" />
            )
        } else if (previewFile.FileType.includes("pdf") || previewFile.Filename.endsWith(".pdf")) {
            mediaElement = (
                <div className="pdf-preview-wrapper">
                    <iframe 
                        src={`/api/download/${previewFile.FileID}#toolbar=0`} 
                        title="PDF Preview" 
                        className="file-preview-pdf"
                    />
                </div>
            )
        } else if (previewFile.FileType.includes("video") || previewFile.Filename.endsWith(".mp4") || previewFile.Filename.endsWith(".avi")) {
            mediaElement = (
                <video controls className="file-preview-video">
                    <source src={`/api/download/${previewFile.FileID}`} />
                </video>
            )
        } else if (previewFile.FileType.includes("audio") || previewFile.Filename.endsWith(".mp3") || previewFile.Filename.endsWith(".wav") || previewFile.Filename.endsWith(".m4a")) {
            mediaElement = (
                <audio controls className="file-preview-audio">
                    <source src={`/api/download/${previewFile.FileID}`} />
                </audio>
            )
        }

        previewBoxElement = (
            <div className="preview-box">
                <hr />
                <h4>Просмотр: {previewFile.Filename}</h4>
                {mediaElement}
                <br />
                <button onClick={() => setPreviewFile(null)}>✘ Закрыть предпросмотр</button>
            </div>
        )
    }

    return (
        <div className="file-manager-container">
            <h3>Мой Диск</h3>

            <div className="upload-section">
                <label>Загрузить файл: </label>
                <input type="file" onChange={handleFileUpload} />
                {uploadStatusElement}
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
                    {tableRowsElement}
                </tbody>
            </table>

            {/* Окно генерации сгорающей ссылки */}
            {shareBoxElement}

            {/* Окно предпросмотра выбранного файла */}
            {previewBoxElement}
        </div>
    )
}