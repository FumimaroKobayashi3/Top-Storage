import { useState, useEffect } from "react"

export default function TrashBin({ SetScreen }) {
    const [trashFiles, setTrashFiles] = useState([])

    function loadTrash() {
        fetch('http://127.0.0.1:8000/api/trash')
            .then(res => res.json())
            .then(data => setTrashFiles(data))
            .catch(err => console.log("Ошибка загрузки корзины:", err))
    }

    useEffect(() => {
        loadTrash()
    }, [])

    function restoreFile(id) {
        fetch(`http://127.0.0.1:8000/api/trash/restore/${id}`, { method: 'POST' })
            .then(() => loadTrash())
    }

    function deletePermanently(id) {
        fetch(`http://127.0.0.1:8000/api/files/${id}`, { method: 'DELETE' })
            .then(() => loadTrash())
    }

    function emptyTrash() {
        fetch('http://127.0.0.1:8000/api/trash/empty', { method: 'DELETE' })
            .then(() => loadTrash())
    }

    return (
        <div className="trash-container">
            <h3>♻ Корзина</h3>

            {trashFiles.length > 0 ? (
                <button onClick={emptyTrash} className="danger-button">✘ Очистить корзину</button>
            ) : null}

            <table className="storage-table">
                <thead>
                    <tr>
                        <th>Имя файла</th>
                        <th>Размер (байт)</th>
                        <th>Дата</th>
                        <th>Действия</th>
                    </tr>
                </thead>
                <tbody>
                    {trashFiles.length === 0 ? (
                        <tr>
                            <td colSpan="4">Корзина пуста</td>
                        </tr>
                    ) : (
                        trashFiles.map(file => (
                            <tr key={file.FileID}>
                                <td>{file.Filename}</td>
                                <td>{file.FileSize}</td>
                                <td>{file.UploadDate}</td>
                                <td>
                                    <button onClick={() => restoreFile(file.FileID)}>🔄 Восстановить</button>
                                    <button onClick={() => deletePermanently(file.FileID)} className="danger-button">✘ Удалить окончательно</button>
                                </td>
                            </tr>
                        ))
                    )}
                </tbody>
            </table>

            <br />
            <button onClick={() => SetScreen("FileManager")}>⬅️ Назад на Диск</button>
        </div>
    )
}