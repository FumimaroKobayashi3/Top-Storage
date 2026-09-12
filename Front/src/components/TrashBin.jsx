import { useState, useEffect } from "react"

export default function TrashBin({ SetScreen }) {
    const [trashFiles, setTrashFiles] = useState([])

    function loadTrash() {
        fetch('/api/trash')
            .then(res => res.json())
            .then(data => setTrashFiles(data))
            .catch(err => console.log("Ошибка загрузки корзины:", err))
    }

    useEffect(() => {
        loadTrash()
    }, [])

    function restoreFile(id) {
        fetch(`/api/trash/restore/${id}`, { method: 'POST' })
            .then(() => loadTrash())
    }

    function deletePermanently(id) {
        fetch(`/api/files/${id}`, { method: 'DELETE' })
            .then(() => loadTrash())
    }

    function emptyTrash() {
        fetch('/api/trash/empty', { method: 'DELETE' })
            .then(() => loadTrash())
    }

    let emptyTrashButtonElement = null
    if (trashFiles.length > 0) {
        emptyTrashButtonElement = (
            <button onClick={emptyTrash} className="danger-button">✘ Очистить корзину</button>
        )
    }

    let trashRowsElement = null
    if (trashFiles.length === 0) {
        trashRowsElement = (
            <tr>
                <td colSpan="4">Корзина пуста</td>
            </tr>
        )
    } else {
        trashRowsElement = trashFiles.map(file => (
            <tr key={file.FileID}>
                <td>{file.Filename}</td>
                <td>{file.FileSize}</td>
                <td>{file.UploadDate}</td>
                <td>
                    <button onClick={() => restoreFile(file.FileID)}>Восстановить</button>
                    <button onClick={() => deletePermanently(file.FileID)} className="danger-button">✘ Удалить окончательно</button>
                </td>
            </tr>
        ))
    }

    return (
        <div className="trash-container">
            <h3>♻ Корзина</h3>

            {emptyTrashButtonElement}

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
                    {trashRowsElement}
                </tbody>
            </table>

            <br />
            <button onClick={() => SetScreen("FileManager")}>⬅ Назад на Диск</button>
        </div>
    )
}