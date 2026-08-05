import { useState, useEffect } from "react"

export default function FileManager({ SetScreen }) {
    const [filesList, setFilesList] = useState([])
    const [selectedCategory, setSelectedCategory] = useState("ALL")
    const [previewFile, setPreviewFile] = useState(null)
    const [previewTextContent, setPreviewTextContent] = useState("")
    const [uploadStatus, setUploadStatus] = useState("")

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
            return file.FileType.includes("video")
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
                <button onClick={() => setSelectedCategory("VIDEO")}>Видео</button>
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
                                    <button onClick={() => moveToTrash(file.FileID)} className="danger-button">🗑️ В корзину</button>
                                </td>
                            </tr>
                        ))
                    )}
                </tbody>
            </table>

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

                    {previewFile.FileType.includes("pdf") ? (
                        <iframe 
                            src={`http://127.0.0.1:8000/api/download/${previewFile.FileID}`} 
                            title="PDF Preview" 
                            width="100%" 
                            height="400px" 
                        />
                    ) : null}

                    {previewFile.FileType.includes("video") ? (
                        <video controls width="100%">
                            <source src={`http://127.0.0.1:8000/api/download/${previewFile.FileID}`} />
                        </video>
                    ) : null}

                    <br />
                    <button onClick={() => setPreviewFile(null)}>✘ Закрыть предпросмотр</button>
                </div>
            ) : null}
        </div>
    )
}