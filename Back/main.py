from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
import hashlib
import sqlite3
import InitDB
import uuid
import time
from dotenv import load_dotenv

# Загружаем ключ из .env
load_dotenv()

# Автоматическая инициализация базы при старте скрипта
InitDB.init_db()

app = FastAPI()
VT_KEY = os.getenv('VT_KEY')

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

# Статистика диска
@app.get("/api/stats")
def getStorageStats():
    connection = sqlite3.connect('Top.db')
    cursor = connection.cursor()

    cursor.execute("SELECT SUM(FileSize), COUNT(*) FROM FILESDB WHERE IsTrash = 0")
    row = cursor.fetchone()
    used_bytes = row[0] if row and row[0] else 0
    total_files = row[1] if row and row[1] else 0

    cursor.execute("SELECT COUNT(*) FROM SECURITYDB WHERE EventType = 'VIRUS_BLOCKED'")
    blocked_viruses = cursor.fetchone()[0]

    cursor.execute("SELECT StorageLimitBytes FROM PETSETTINGSDB WHERE SettingID = 1")
    setting = cursor.fetchone()
    limit_bytes = setting[0] if setting else 42949672960

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
    return [{
        "FileID": r[0], "Filename": r[1], "Filepath": r[2],
        "FileSize": r[3], "FileType": r[4], "FileHash": r[5], "UploadDate": r[6]
    } for r in rows]

# Список файлов в корзине
@app.get("/api/trash")
def getTrashFiles():
    connection = sqlite3.connect('Top.db')
    cursor = connection.cursor()
    cursor.execute("SELECT FileID, Filename, Filepath, FileSize, FileType, UploadDate FROM FILESDB WHERE IsTrash = 1 ORDER BY FileID DESC")
    rows = cursor.fetchall()
    connection.close()
    return [{
        "FileID": r[0], "Filename": r[1], "Filepath": r[2],
        "FileSize": r[3], "FileType": r[4], "UploadDate": r[5]
    } for r in rows]

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
    for r in rows:
        clean_filename = os.path.basename(r[0])
        real_path = os.path.join(UPLOAD_DIR, clean_filename)
        if os.path.exists(real_path):
            try:
                os.remove(real_path)
            except Exception:
                pass
    cursor.execute("DELETE FROM FILESDB WHERE IsTrash = 1")
    connection.commit()
    connection.close()
    return {"status": "ok", "message": "Корзина успешно очищена"}

# Загрузка файлов
@app.post("/api/upload")
async def uploadFile(file: UploadFile = File(...)):
    file_bytes = await file.read()
    file_size = len(file_bytes)
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    content_type = file.content_type or "application/octet-stream"

    connection = sqlite3.connect('Top.db')
    cursor = connection.cursor()

    cursor.execute("SELECT SUM(FileSize) FROM FILESDB WHERE IsTrash = 0")
    row = cursor.fetchone()
    current_used = row[0] if row and row[0] else 0
    limit_bytes = 42949672960

    if current_used + file_size > limit_bytes:
        connection.close()
        return {"status": "error", "message": "Превышен лимит хранилища 40 ГБ!"}

    # VirusTotal API
    headers = {"x-apikey": VT_KEY}
    vt_url = f"https://www.virustotal.com/api/v3/files/{file_hash}"
    ant_count = 0
    total_ant = 0
    scan_result_text = "Файл ранее не встречался в базе VirusTotal"

    try:
        vt_response = requests.get(vt_url, headers=headers, timeout=5)
        if vt_response.status_code == 200:
            stats = vt_response.json()['data']['attributes']['last_analysis_stats']
            ant_count = stats['malicious']
            total_ant = sum(stats.values())
            scan_result_text = f"Обнаружено угроз: {ant_count} из {total_ant}"
        elif vt_response.status_code == 404:
            scan_result_text = "Файл чист (хэш в базе вредоносов не найден)"
    except Exception:
        scan_result_text = "Ошибка связи с сервером проверки угроз (таймаут)"

    if ant_count >= 20:
        cursor.execute("""
            INSERT INTO SECURITYDB (EventType, Details, FileName, FileHash, ScanResult, AntVirCounter, TotalAntViruses)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("VIRUS_BLOCKED", "Загрузка заблокирована системой безопасности", file.filename, file_hash, scan_result_text, ant_count, total_ant))
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
    """, (file.filename, file_path, file_size, content_type, file_hash))

    cursor.execute("""
        INSERT INTO SECURITYDB (EventType, Details, FileName, FileHash, ScanResult, AntVirCounter, TotalAntViruses)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ("FILE_APPROVED", "Файл успешно проверен и сохранен", file.filename, file_hash, scan_result_text, ant_count, total_ant))

    connection.commit()
    connection.close()
    return {"status": "ok", "message": "Файл успешно загружен в хранилище!"}

# Скачивание файла по ID
@app.get("/api/download/{file_id}")
def downloadFile(file_id: int):
    connection = sqlite3.connect('Top.db')
    cursor = connection.cursor()
    cursor.execute("SELECT Filename, Filepath, FileType FROM FILESDB WHERE FileID = ?", (file_id,))
    row = cursor.fetchone()
    connection.close()

    if row:
        clean_filename = os.path.basename(row[1])
        real_path = os.path.join(UPLOAD_DIR, clean_filename)
        if os.path.exists(real_path):
            return FileResponse(path=real_path, filename=row[0], media_type=row[2])
        raise HTTPException(status_code=404, detail="Файл на диске не найден")
    raise HTTPException(status_code=404, detail="Запись о файле не найдена")

# Окончательное удаление файла
@app.delete("/api/files/{file_id}")
def deleteFile(file_id: int):
    connection = sqlite3.connect('Top.db')
    cursor = connection.cursor()
    cursor.execute("SELECT Filepath, Filename FROM FILESDB WHERE FileID = ?", (file_id,))
    row = cursor.fetchone()
    if row:
        clean_filename = os.path.basename(row[0])
        real_path = os.path.join(UPLOAD_DIR, clean_filename)
        if os.path.exists(real_path):
            os.remove(real_path)
        cursor.execute("DELETE FROM FILESDB WHERE FileID = ?", (file_id,))
        connection.commit()
        connection.close()
        return {"status": "ok", "message": f"Файл {row[1]} окончательно удален"}
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
    return [{
        "LogId": r[0], "EventType": r[1], "Details": r[2], "FileName": r[3],
        "FileHash": r[4], "ScanResult": r[5], "AntVirCounter": r[6],
        "TotalAntViruses": r[7], "Timestamp": r[8]
    } for r in rows]

# Генерация сгорающей ссылки
@app.post("/api/files/share/{file_id}")
def createLink(file_id: int, hours: int = 72):
    connection = sqlite3.connect('Top.db')
    cursor = connection.cursor()
    cursor.execute("SELECT FileID FROM FILESDB WHERE FileID = ? AND IsTrash = 0", (file_id,))
    row = cursor.fetchone()
    if not row:
        connection.close()
        raise HTTPException(status_code=404, detail="Файл не найден")

    current_time = int(time.time())
    expired_timestamp = current_time + (hours * 3600) if hours > 0 else 0
    unique_code = str(uuid.uuid4())[:8]
    public_token = f"{unique_code}_{expired_timestamp}"

    cursor.execute("UPDATE FILESDB SET IsPublic = 1, PublicToken = ? WHERE FileID = ?", (public_token, file_id))
    connection.commit()
    connection.close()
    return {"status": "ok", "public_url": f"http://127.0.0.1:8000/api/public/download/{public_token}"}

# Скачивание по сгорающей ссылке
@app.get("/api/public/download/{token}")
def downloadPubFile(token: str):
    connection = sqlite3.connect('Top.db')
    cursor = connection.cursor()
    cursor.execute("SELECT FileID, Filename, Filepath, FileType FROM FILESDB WHERE IsPublic = 1 AND PublicToken = ?", (token,))
    row = cursor.fetchone()

    if row:
        file_id, filename, raw_filepath, filetype = row[0], row[1], row[2], row[3]
        token_parts = token.split("_")
        expired_timestamp = int(token_parts[1])
        current_time = int(time.time())

        if expired_timestamp != 0 and current_time > expired_timestamp:
            cursor.execute("UPDATE FILESDB SET IsPublic = 0, PublicToken = NULL WHERE FileID = ?", (file_id,))
            connection.commit()
            connection.close()
            raise HTTPException(status_code=410, detail="Ссылка сгорела")

        connection.close()
        clean_filename = os.path.basename(raw_filepath)
        real_path = os.path.join(UPLOAD_DIR, clean_filename)
        if os.path.exists(real_path):
            return FileResponse(path=real_path, filename=filename, media_type=filetype)
        raise HTTPException(status_code=404, detail="Файл физически не найден")

    connection.close()
    raise HTTPException(status_code=404, detail="Ссылка недействительна")