from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
import hashlib
import sqlite3
import InitDB

app = FastAPI()

VT_KEY = '2a194e93d6510f2ab2b4d304914c1cd3fc3eb02fe25c5b2e3862bd013e461d47'

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def mainpageServing():
    return RedirectResponse(url='http://localhost:5173')

# Статистика хранилища
@app.get("/api/stats")
def getStorageStats():
    connection = sqlite3.connect('Top.db')
    cursor = connection.cursor()

    cursor.execute("SELECT SUM(FileSize), COUNT(*) FROM FILESDB WHERE IsTrash = 0")
    row = cursor.fetchone()

    used_bytes = 0
    total_files = 0

    if row:
        if row[0]:
            used_bytes = row[0]
        if row[1]:
            total_files = row[1]

    cursor.execute("SELECT COUNT(*) FROM SECURITYDB WHERE EventType = 'VIRUS_BLOCKED'")
    blocked_viruses = cursor.fetchone()[0]

    cursor.execute("SELECT StorageLimitBytes FROM PETSETTINGSDB WHERE SettingID = 1")
    setting = cursor.fetchone()

    limit_bytes = 42949672960
    if setting:
        if setting[0]:
            limit_bytes = setting[0]

    connection.close()

    return {
        "used_bytes": used_bytes,
        "limit_bytes": limit_bytes,
        "total_files": total_files,
        "blocked_viruses": blocked_viruses
    }

# Список активных файлов
@app.get("/api/files")
def getFilesList():
    connection = sqlite3.connect('Top.db')
    cursor = connection.cursor()
    cursor.execute("SELECT FileID, Filename, Filepath, FileSize, FileType, FileHash, UploadDate FROM FILESDB WHERE IsTrash = 0 ORDER BY FileID DESC")
    rows = cursor.fetchall()
    connection.close()

    files_list = []
    for row in rows:
        files_list.append({
            "FileID": row[0],
            "Filename": row[1],
            "Filepath": row[2],
            "FileSize": row[3],
            "FileType": row[4],
            "FileHash": row[5],
            "UploadDate": row[6]
        })
    return files_list

# Список файлов в корзине
@app.get("/api/trash")
def getTrashFiles():
    connection = sqlite3.connect('Top.db')
    cursor = connection.cursor()
    cursor.execute("SELECT FileID, Filename, Filepath, FileSize, FileType, UploadDate FROM FILESDB WHERE IsTrash = 1 ORDER BY FileID DESC")
    rows = cursor.fetchall()
    connection.close()

    trash_list = []
    for row in rows:
        trash_list.append({
            "FileID": row[0],
            "Filename": row[1],
            "Filepath": row[2],
            "FileSize": row[3],
            "FileType": row[4],
            "UploadDate": row[5]
        })
    return trash_list

# Перемещение в корзину
@app.post("/api/trash/move/{file_id}")
def moveToTrash(file_id: int):
    connection = sqlite3.connect('Top.db')
    cursor = connection.cursor()
    cursor.execute("UPDATE FILESDB SET IsTrash = 1 WHERE FileID = ?", (file_id,))
    connection.commit()
    connection.close()
    return {"status": "ok", "message": "Файл перемещен в корзину"}

# Восстановление из корзины
@app.post("/api/trash/restore/{file_id}")
def restoreFromTrash(file_id: int):
    connection = sqlite3.connect('Top.db')
    cursor = connection.cursor()
    cursor.execute("UPDATE FILESDB SET IsTrash = 0 WHERE FileID = ?", (file_id,))
    connection.commit()
    connection.close()
    return {"status": "ok", "message": "Файл восстановлен из корзины"}

# Очистка корзины
@app.delete("/api/trash/empty")
def emptyTrash():
    connection = sqlite3.connect('Top.db')
    cursor = connection.cursor()
    cursor.execute("SELECT Filepath FROM FILESDB WHERE IsTrash = 1")
    rows = cursor.fetchall()

    for row in rows:
        file_path = row[0]
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

    cursor.execute("DELETE FROM FILESDB WHERE IsTrash = 1")
    connection.commit()
    connection.close()
    return {"status": "ok", "message": "Корзина успешно очищена"}

# Загрузка и проверка файла
@app.post("/api/upload")
async def uploadFile(file: UploadFile = File(...)):
    file_bytes = await file.read()
    file_size = len(file_bytes)
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    connection = sqlite3.connect('Top.db')
    cursor = connection.cursor()

    cursor.execute("SELECT SUM(FileSize) FROM FILESDB WHERE IsTrash = 0")
    row = cursor.fetchone()

    current_used = 0
    if row:
        if row[0]:
            current_used = row[0]

    limit_bytes = 42949672960

    if current_used + file_size > limit_bytes:
        connection.close()
        return {"status": "error", "message": "Превышен лимит хранилища 40 ГБ!"}

    headers = {"x-apikey": VT_KEY}
    vt_url = f"https://www.virustotal.com/api/v3/files/{file_hash}"
    
    ant_count = 0
    total_ant = 0
    scan_result_text = "Файл ранее не встречался в базе VirusTotal"

    try:
        vt_response = requests.get(vt_url, headers=headers, timeout=5)
        if vt_response.status_code == 200:
            vt_data = vt_response.json()
            stats = vt_data['data']['attributes']['last_analysis_stats']
            ant_count = stats['malicious']

            for count in stats.values():
                total_ant = total_ant + count

            scan_result_text = f"Обнаружено угроз: {ant_count} из {total_ant}"
        else:
            if vt_response.status_code == 404:
                scan_result_text = "Файл чист (хэш в базе вредоносов не найден)"
    except Exception:
        scan_result_text = "Ошибка связи с сервером проверки угроз (таймаут)"

    if ant_count >= 20:
        cursor.execute("""
            INSERT INTO SECURITYDB (EventType, Details, FileName, FileHash, ScanResult, AntVirCounter, TotalAntViruses)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("VIRUS_BLOCKED", "Загрузка заблокирована с", file.filename, file_hash, scan_result_text, ant_count, total_ant))
        connection.commit()
        connection.close()
        return {"status": "blocked", "message": f"Файл заблокирован! Обнаружено угроз: {ant_count}"}

    unique_filename = f"{file_hash[:8]}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    with open(file_path, "wb") as buffer:
        buffer.write(file_bytes)

    cursor.execute("""
        INSERT INTO FILESDB (Filename, Filepath, FileSize, FileType, FileHash, IsTrash)
        VALUES (?, ?, ?, ?, ?, 0)
    """, (file.filename, file_path, file_size, file.content_type, file_hash))

    cursor.execute("""
        INSERT INTO SECURITYDB (EventType, Details, FileName, FileHash, ScanResult, AntVirCounter, TotalAntViruses)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ("FILE_APPROVED", "Файл успешно проверен и сохранен", file.filename, file_hash, scan_result_text, ant_count, total_ant))

    connection.commit()
    connection.close()
    return {"status": "ok", "message": "Файл успешно загружен "}

# Скачивание файла по ID
@app.get("/api/download/{file_id}")
def downloadFile(file_id: int):
    connection = sqlite3.connect('Top.db')
    cursor = connection.cursor()
    cursor.execute("SELECT Filename, Filepath, FileType FROM FILESDB WHERE FileID = ?", (file_id,))
    row = cursor.fetchone()
    connection.close()

    if row:
        file_path = row[1]
        if os.path.exists(file_path):
            return FileResponse(path=file_path, filename=row[0], media_type=row[2])
        else:
            raise HTTPException(status_code=404, detail="Файл на диске не найден")

    raise HTTPException(status_code=404, detail="Запись о файле не найдена")

# Удаление файла
@app.delete("/api/files/{file_id}")
def deleteFile(file_id: int):
    connection = sqlite3.connect('Top.db')
    cursor = connection.cursor()
    cursor.execute("SELECT Filepath, Filename FROM FILESDB WHERE FileID = ?", (file_id,))
    row = cursor.fetchone()

    if row:
        file_path = row[0]
        filename = row[1]

        if os.path.exists(file_path):
            os.remove(file_path)

        cursor.execute("DELETE FROM FILESDB WHERE FileID = ?", (file_id,))
        connection.commit()
        connection.close()
        return {"status": "ok", "message": f"Файл {filename} окончательно удален"}

    connection.close()
    return {"status": "error", "message": "Файл не найден"}

# Логи безопасности
@app.get("/api/logs")
def getSecurityLogs():
    connection = sqlite3.connect('Top.db')
    cursor = connection.cursor()
    cursor.execute("SELECT LogId, EventType, Details, FileName, FileHash, ScanResult, AntVirCounter, TotalAntViruses, Timestamp FROM SECURITYDB ORDER BY LogId DESC")
    rows = cursor.fetchall()
    connection.close()

    logs_list = []
    for row in rows:
        logs_list.append({
            "LogId": row[0],
            "EventType": row[1],
            "Details": row[2],
            "FileName": row[3],
            "FileHash": row[4],
            "ScanResult": row[5],
            "AntVirCounter": row[6],
            "TotalAntViruses": row[7],
            "Timestamp": row[8]
        })
    return logs_list