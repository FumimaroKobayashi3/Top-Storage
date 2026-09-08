from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from dotenv import load_dotenv
import os
import requests
import hashlib
import sqlite3
import uuid
import time
import shutil

try:
    import InitDB
except ImportError:
    from Back import InitDB

# Чтение переменных окружения

load_dotenv()  # подхватит .env, если он лежит рядом
VT_KEY = os.getenv("VT_KEY", "").strip()  # заберёт ключ из панели Амверы ИЛИ из .env

# Пути к данным: если смонтирован диск Амверы /data — пишем туда
if Path("/data").exists():
    DB_PATH = Path("/data/Top.db")
    UPLOAD_DIR = Path("/data/uploads")
else:
    DB_PATH = Path("Top.db")
    UPLOAD_DIR = Path("uploads")

if not UPLOAD_DIR.exists():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Инициализация схемы базы данных
try:
    InitDB.init_db(DB_PATH)
except TypeError:
    InitDB.init_db()

# Проверка колонок под сгорающие ссылки (защита от ошибок старой базы)
def check_db_schema():
    connection = sqlite3.connect(DB_PATH, timeout=30)
    cursor = connection.cursor()
    cursor.execute("PRAGMA table_info(FILESDB)")
    existing_cols = []
    for col in cursor.fetchall():
        existing_cols.append(col[1])

    if "IsPublic" not in existing_cols:
        cursor.execute("ALTER TABLE FILESDB ADD COLUMN IsPublic INTEGER DEFAULT 0")
    if "PublicToken" not in existing_cols:
        cursor.execute("ALTER TABLE FILESDB ADD COLUMN PublicToken TEXT")

    connection.commit()
    connection.close()

check_db_schema()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статистика хранилища
@app.get("/api/stats")
def getStorageStats():
    connection = sqlite3.connect(DB_PATH, timeout=30)
    cursor = connection.cursor()

    cursor.execute("SELECT SUM(FileSize), COUNT(*) FROM FILESDB WHERE IsTrash = 0")
    row = cursor.fetchone()

    used_bytes = 0
    total_files = 0
    if row is not None:
        if row[0] is not None:
            used_bytes = row[0]
        if row[1] is not None:
            total_files = row[1]

    cursor.execute("SELECT COUNT(*) FROM SECURITYDB WHERE EventType = 'VIRUS_BLOCKED'")
    blocked_row = cursor.fetchone()
    blocked_viruses = 0
    if blocked_row is not None:
        blocked_viruses = blocked_row[0]

    cursor.execute("SELECT StorageLimitBytes FROM PETSETTINGSDB WHERE SettingID = 1")
    setting = cursor.fetchone()

    limit_bytes = 42949672960
    if setting is not None:
        if setting[0] is not None:
            limit_bytes = setting[0]

    connection.close()

    return {
        "used_bytes": used_bytes,
        "limit_bytes": limit_bytes,
        "total_files": total_files,
        "blocked_viruses": blocked_viruses
    }

# Список файлов
@app.get("/api/files")
def getFilesList():
    connection = sqlite3.connect(DB_PATH, timeout=30)
    cursor = connection.cursor()
    cursor.execute(
        "SELECT FileID, Filename, Filepath, FileSize, FileType, FileHash, UploadDate "
        "FROM FILESDB WHERE IsTrash = 0 ORDER BY FileID DESC"
    )
    rows = cursor.fetchall()
    connection.close()

    result = []
    for r in rows:
        result.append({
            "FileID": r[0],
            "Filename": r[1],
            "Filepath": r[2],
            "FileSize": r[3],
            "FileType": r[4],
            "FileHash": r[5],
            "UploadDate": r[6]
        })

    return result

# Список файлов в корзине
@app.get("/api/trash")
def getTrashFiles():
    connection = sqlite3.connect(DB_PATH, timeout=30)
    cursor = connection.cursor()
    cursor.execute(
        "SELECT FileID, Filename, Filepath, FileSize, FileType, UploadDate "
        "FROM FILESDB WHERE IsTrash = 1 ORDER BY FileID DESC"
    )
    rows = cursor.fetchall()
    connection.close()

    result = []
    for r in rows:
        result.append({
            "FileID": r[0],
            "Filename": r[1],
            "Filepath": r[2],
            "FileSize": r[3],
            "FileType": r[4],
            "UploadDate": r[5]
        })

    return result

# Перемещение в корзину
@app.post("/api/trash/move/{file_id}")
def moveToTrash(file_id: int):
    connection = sqlite3.connect(DB_PATH, timeout=30)
    cursor = connection.cursor()
    cursor.execute("UPDATE FILESDB SET IsTrash = 1 WHERE FileID = ?", (file_id,))
    connection.commit()
    connection.close()
    return {"status": "ok", "message": "Файл перемещен в корзину"}

# Восстановление из корзины
@app.post("/api/trash/restore/{file_id}")
def restoreFromTrash(file_id: int):
    connection = sqlite3.connect(DB_PATH, timeout=30)
    cursor = connection.cursor()
    cursor.execute("UPDATE FILESDB SET IsTrash = 0 WHERE FileID = ?", (file_id,))
    connection.commit()
    connection.close()
    return {"status": "ok", "message": "Файл восстановлен из корзины"}

# Очистка корзины
@app.delete("/api/trash/empty")
def emptyTrash():
    connection = sqlite3.connect(DB_PATH, timeout=30)
    cursor = connection.cursor()
    cursor.execute("SELECT Filepath FROM FILESDB WHERE IsTrash = 1")
    rows = cursor.fetchall()

    for r in rows:
        clean_filename = Path(r[0]).name
        real_path = UPLOAD_DIR / clean_filename
        if not real_path.exists():
            real_path = Path(r[0])

        if real_path.exists():
            try:
                real_path.unlink()
            except Exception:
                pass

    cursor.execute("DELETE FROM FILESDB WHERE IsTrash = 1")
    connection.commit()
    connection.close()
    return {"status": "ok", "message": "Корзина успешно очищена"}

# Загрузка файлов (потоковая, безопасная для RAM сервера)
@app.post("/api/upload")
async def uploadFile(file: UploadFile = File(...)):
    # Временный файл для подсчёта хэша без загрузки всего файла в оперативку
    temp_file_path = UPLOAD_DIR / f"temp_{uuid.uuid4().hex}"
    sha256_hash = hashlib.sha256()
    file_size = 0

    try:
        with open(temp_file_path, "wb") as buffer:
            while True:
                chunk = await file.read(1024 * 1024)  # Читаем кусками по 1 МБ
                if not chunk:
                    break
                file_size += len(chunk)
                sha256_hash.update(chunk)
                buffer.write(chunk)
    except Exception as e:
        if temp_file_path.exists():
            temp_file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Ошибка записи файла: {e}")

    file_hash = sha256_hash.hexdigest()

    # Определение типа файла
    fn_lower = file.filename.lower()
    if fn_lower.endswith(".pdf"):
        content_type = "application/pdf"
    elif fn_lower.endswith(".mp4"):
        content_type = "video/mp4"
    elif fn_lower.endswith(".rar"):
        content_type = "application/x-rar-compressed"
    elif file.content_type:
        content_type = file.content_type
    else:
        content_type = "application/octet-stream"

    connection = sqlite3.connect(DB_PATH, timeout=30)
    cursor = connection.cursor()

    # Проверка общего лимита хранилища
    cursor.execute("SELECT SUM(FileSize) FROM FILESDB WHERE IsTrash = 0")
    row = cursor.fetchone()

    current_used = 0
    if row is not None:
        if row[0] is not None:
            current_used = row[0]

    limit_bytes = 42949672960
    if current_used + file_size > limit_bytes:
        if temp_file_path.exists():
            temp_file_path.unlink()
        connection.close()
        return {"status": "error", "message": "Превышен лимит хранилища 40 ГБ!"}

    # Проверка VirusTotal
    ant_count = 0
    total_ant = 0
    scan_result_text = "Проверка отключена"

    if VT_KEY:
        headers = {"x-apikey": VT_KEY}
        vt_url = f"https://www.virustotal.com/api/v3/files/{file_hash}"
        try:
            vt_response = requests.get(vt_url, headers=headers, timeout=2)
            if vt_response.status_code == 200:
                stats = vt_response.json()["data"]["attributes"]["last_analysis_stats"]
                ant_count = stats["malicious"]
                total_ant = sum(stats.values())
                scan_result_text = f"Обнаружено угроз: {ant_count} из {total_ant}"
            elif vt_response.status_code == 404:
                scan_result_text = "Файл чист (хэш в базе вредоносов не найден)"
            else:
                scan_result_text = f"Статус проверки: {vt_response.status_code}"
        except Exception:
            scan_result_text = "Проверка пропущена (таймаут или блокировка сервиса)"

    if ant_count >= 20:
        if temp_file_path.exists():
            temp_file_path.unlink()
        cursor.execute(
            "INSERT INTO SECURITYDB (EventType, Details, FileName, FileHash, ScanResult, AntVirCounter, TotalAntViruses) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("VIRUS_BLOCKED", "Загрузка заблокирована системой безопасности", file.filename, file_hash, scan_result_text, ant_count, total_ant)
        )
        connection.commit()
        connection.close()
        return {"status": "blocked", "message": f"Файл заблокирован! Обнаружено угроз: {ant_count}"}

    final_filename = f"{file_hash[:8]}_{file.filename}"
    final_path = UPLOAD_DIR / final_filename

    # Если такой файл уже физически лежит на диске — удаляем временный
    if final_path.exists():
        if temp_file_path.exists():
            temp_file_path.unlink()
    else:
        shutil.move(str(temp_file_path), str(final_path))

    cursor.execute(
        "INSERT INTO FILESDB (Filename, Filepath, FileSize, FileType, FileHash, IsTrash) "
        "VALUES (?, ?, ?, ?, ?, 0)",
        (file.filename, str(final_path), file_size, content_type, file_hash)
    )

    cursor.execute(
        "INSERT INTO SECURITYDB (EventType, Details, FileName, FileHash, ScanResult, AntVirCounter, TotalAntViruses) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("FILE_APPROVED", "Файл успешно проверен и сохранен", file.filename, file_hash, scan_result_text, ant_count, total_ant)
    )

    connection.commit()
    connection.close()
    return {"status": "ok", "message": "Файл успешно загружен в хранилище!"}

# Скачивание файла по ID
@app.get("/api/download/{file_id}")
def downloadFile(file_id: int):
    connection = sqlite3.connect(DB_PATH, timeout=30)
    cursor = connection.cursor()
    cursor.execute("SELECT Filename, Filepath, FileType FROM FILESDB WHERE FileID = ?", (file_id,))
    row = cursor.fetchone()
    connection.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Запись о файле не найдена")

    filename = row[0]
    raw_filepath = row[1]
    media_type = row[2]

    clean_filename = Path(raw_filepath).name
    real_path = UPLOAD_DIR / clean_filename
    if not real_path.exists():
        real_path = Path(raw_filepath)

    if not real_path.exists():
        raise HTTPException(status_code=404, detail="Файл на диске не найден")

    if filename.lower().endswith(".pdf"):
        media_type = "application/pdf"

    return FileResponse(
        path=str(real_path),
        media_type=media_type,
        content_disposition_type="inline"
    )

# Удаление файла
@app.delete("/api/files/{file_id}")
def deleteFile(file_id: int):
    connection = sqlite3.connect(DB_PATH, timeout=30)
    cursor = connection.cursor()
    cursor.execute("SELECT Filepath, Filename FROM FILESDB WHERE FileID = ?", (file_id,))
    row = cursor.fetchone()

    if row is None:
        connection.close()
        return {"status": "error", "message": "Файл не найден"}

    clean_filename = Path(row[0]).name
    real_path = UPLOAD_DIR / clean_filename
    if not real_path.exists():
        real_path = Path(row[0])

    if real_path.exists():
        try:
            real_path.unlink()
        except Exception:
            pass

    cursor.execute("DELETE FROM FILESDB WHERE FileID = ?", (file_id,))
    connection.commit()
    connection.close()
    return {"status": "ok", "message": f"Файл {row[1]} окончательно удален"}

# Логи безопасности
@app.get("/api/logs")
def getSecurityLogs():
    connection = sqlite3.connect(DB_PATH, timeout=30)
    cursor = connection.cursor()
    cursor.execute(
        "SELECT LogId, EventType, Details, FileName, FileHash, ScanResult, AntVirCounter, TotalAntViruses, Timestamp "
        "FROM SECURITYDB ORDER BY LogId DESC"
    )
    rows = cursor.fetchall()
    connection.close()

    result = []
    for r in rows:
        result.append({
            "LogId": r[0],
            "EventType": r[1],
            "Details": r[2],
            "FileName": r[3],
            "FileHash": r[4],
            "ScanResult": r[5],
            "AntVirCounter": r[6],
            "TotalAntViruses": r[7],
            "Timestamp": r[8]
        })

    return result

# Генерация сгорающей ссылки
@app.post("/api/files/share/{file_id}")
def createLink(file_id: int, request: Request, hours: int = 72):
    connection = sqlite3.connect(DB_PATH, timeout=30)
    cursor = connection.cursor()
    cursor.execute("SELECT FileID FROM FILESDB WHERE FileID = ? AND IsTrash = 0", (file_id,))
    row = cursor.fetchone()

    if row is None:
        connection.close()
        raise HTTPException(status_code=404, detail="Файл не найден")

    current_time = int(time.time())

    if hours > 0:
        expired_timestamp = current_time + (hours * 3600)
    else:
        expired_timestamp = 0

    unique_code = str(uuid.uuid4())[:8]
    public_token = f"{unique_code}_{expired_timestamp}"

    cursor.execute("UPDATE FILESDB SET IsPublic = 1, PublicToken = ? WHERE FileID = ?", (public_token, file_id))
    connection.commit()
    connection.close()

    # Определение внешнего адреса приложения (за обратным прокси Амверы)
    host = request.headers.get("x-forwarded-host")
    if not host:
        host = request.headers.get("host")
    if not host:
        host = "127.0.0.1:8000"

    proto = request.headers.get("x-forwarded-proto")
    if not proto:
        proto = request.url.scheme
    if not proto:
        proto = "http"

    public_url = f"{proto}://{host}/api/public/download/{public_token}"
    return {"status": "ok", "public_url": public_url}

# Скачивание по сгорающей ссылке
@app.get("/api/public/download/{token}")
def downloadPubFile(token: str):
    connection = sqlite3.connect(DB_PATH, timeout=30)
    cursor = connection.cursor()
    cursor.execute(
        "SELECT FileID, Filename, Filepath, FileType FROM FILESDB WHERE IsPublic = 1 AND PublicToken = ?",
        (token,)
    )
    row = cursor.fetchone()

    if row is None:
        connection.close()
        raise HTTPException(status_code=404, detail="Ссылка недействительна")

    file_id = row[0]
    filename = row[1]
    raw_filepath = row[2]
    filetype = row[3]

    token_parts = token.rsplit("_", 1)
    expired_timestamp = 0
    if len(token_parts) == 2:
        if token_parts[1].isdigit():
            expired_timestamp = int(token_parts[1])

    current_time = int(time.time())

    if expired_timestamp != 0:
        if current_time > expired_timestamp:
            cursor.execute("UPDATE FILESDB SET IsPublic = 0, PublicToken = NULL WHERE FileID = ?", (file_id,))
            connection.commit()
            connection.close()
            raise HTTPException(status_code=410, detail="Ссылка сгорела")

    connection.close()

    clean_filename = Path(raw_filepath).name
    real_path = UPLOAD_DIR / clean_filename
    if not real_path.exists():
        real_path = Path(raw_filepath)

    if not real_path.exists():
        raise HTTPException(status_code=404, detail="Файл физически не найден")

    if not filetype:
        filetype = "application/octet-stream"

    return FileResponse(
        path=str(real_path),
        filename=filename,
        media_type=filetype
    )

# Раздача фронтенда 
frontend_dist = Path("/app/Front/dist")
if not frontend_dist.exists():
    frontend_dist = Path(__file__).resolve().parent.parent / "Front" / "dist"
if not frontend_dist.exists():
    frontend_dist = Path("Front/dist")

if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
else:
    @app.get("/")
    def mainpageServing():
        return RedirectResponse(url="http://localhost:5173")