from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import hashlib
import sqlite3
import uuid
import time
from Back import InitDB

# Реальный лимит диска для Amvera Standard: 5 ГБ
STORAGE_LIMIT_5GB = 5368709120

# Словарь статусов операций
STATUS_MESSAGES = {
    "SUCCESS": "Файл успешно выложен",
    "STORAGE_FULL": "Не получилось: диск переполнен, удалите старье",
    "PAYLOAD_TOO_LARGE": "Занесите ещё 3к и будет вам на 6 гб ОЗУ и 2 ядра цпу (лимит файла превышен)",
    "SAVE_ERROR": "Не получилось сохранить файл на диск",
    "TRASH_MOVED": "Файл отправлен в корзину",
    "TRASH_RESTORED": "Файл возвращен из корзины"
}

# Пути к данным: на сервере пишем в постоянный раздел /data, локально — рядом со скриптом
if Path("/data").exists():
    DB_PATH = Path("/data/Top.db")
    UPLOAD_DIR = Path("/data/uploads")
else:
    DB_PATH = Path("Top.db")
    UPLOAD_DIR = Path("uploads")

if not UPLOAD_DIR.exists():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Инициализация структуры БД
InitDB.init_db(DB_PATH)

# Проверка колонок под публичные ссылки
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

# Функция для логирования операций в базу
def write_system_log(event_type: str, details: str, filename: str, file_hash: str, scan_result: str):
    connection = sqlite3.connect(DB_PATH, timeout=30)
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO SECURITYDB (EventType, Details, FileName, FileHash, ScanResult, AntVirCounter, TotalAntViruses) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (event_type, details, filename, file_hash, scan_result, 0, 0)
    )
    connection.commit()
    connection.close()

# Статистика занятого места
@app.get("/api/stats")
def getStorageStats():
    connection = sqlite3.connect(DB_PATH, timeout=30)
    cursor = connection.cursor()

    # COALESCE вернёт 0 вместо None, если файлов ещё нет (никаких лишних if)
    cursor.execute("SELECT COALESCE(SUM(FileSize), 0), COUNT(*) FROM FILESDB WHERE IsTrash = 0")
    used_bytes, total_files = cursor.fetchone()

    # Считаем файлы в корзине для третьей карточки
    cursor.execute("SELECT COUNT(*) FROM FILESDB WHERE IsTrash = 1")
    trash_files = cursor.fetchone()[0]

    connection.close()

    return {
        "used_bytes": used_bytes,
        "limit_bytes": STORAGE_LIMIT_5GB,
        "total_files": total_files,
        "trash_files": trash_files
    }
    
def fetch_files_from_db(is_trash: int):
    connection = sqlite3.connect(DB_PATH, timeout=30)
    cursor = connection.cursor()
    cursor.execute(
        "SELECT FileID, Filename, Filepath, FileSize, FileType, FileHash, UploadDate "
        "FROM FILESDB WHERE IsTrash = ? ORDER BY FileID DESC",
        (is_trash,)
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


# Список активных файлов
@app.get("/api/files")
def getFilesList():
    return fetch_files_from_db(is_trash=0)

# Список файлов в корзине
@app.get("/api/trash")
def getTrashFiles():
    return fetch_files_from_db(is_trash=1)

# Управление состоянием корзины (0 - активен, 1 - в корзине)
def set_trash_state(file_id: int, state: int):
    connection = sqlite3.connect(DB_PATH, timeout=30)
    cursor = connection.cursor()
    cursor.execute("UPDATE FILESDB SET IsTrash = ? WHERE FileID = ?", (state, file_id))
    connection.commit()
    connection.close()

@app.post("/api/trash/move/{file_id}")
def moveToTrash(file_id: int):
    set_trash_state(file_id, 1)
    return {"status": "ok", "message": STATUS_MESSAGES["TRASH_MOVED"]}

@app.post("/api/trash/restore/{file_id}")
def restoreFromTrash(file_id: int):
    set_trash_state(file_id, 0)
    return {"status": "ok", "message": STATUS_MESSAGES["TRASH_RESTORED"]}

# Полная очистка корзины
@app.delete("/api/trash/empty")
def emptyTrash():
    connection = sqlite3.connect(DB_PATH, timeout=30)
    cursor = connection.cursor()
    cursor.execute("SELECT Filepath FROM FILESDB WHERE IsTrash = 1")
    rows = cursor.fetchall()

    for r in rows:
        file_disk_path = Path(r[0])
        if file_disk_path.exists():
            try:
                file_disk_path.unlink()
            except OSError:
                pass

    cursor.execute("DELETE FROM FILESDB WHERE IsTrash = 1")
    connection.commit()
    connection.close()
    return {"status": "ok", "message": "Корзина успешно очищена"}

# Загрузка файла 
@app.post("/api/upload")
async def uploadFile(file: UploadFile = File(...)):
    file_bytes = await file.read()
    file_size = len(file_bytes)
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    # Определение MIME-типа
    fn_lower = file.filename.lower()
    if fn_lower.endswith(".pdf"):
        content_type = "application/pdf"
    elif fn_lower.endswith(".rar"):
        content_type = "application/x-rar-compressed"
    elif file.content_type:
        content_type = file.content_type
    else:
        content_type = "application/octet-stream"

    # Проверка лимита диска
    connection = sqlite3.connect(DB_PATH, timeout=30)
    cursor = connection.cursor()
    cursor.execute("SELECT SUM(FileSize) FROM FILESDB WHERE IsTrash = 0")
    row = cursor.fetchone()

    current_used = 0
    if row is not None:
        if row[0] is not None:
            current_used = row[0]

    if current_used + file_size > STORAGE_LIMIT_5GB:
        connection.close()
        write_system_log("LIMIT_EXCEEDED", "Не хватило места на диске", file.filename, file_hash, STATUS_MESSAGES["STORAGE_FULL"])
        return {"status": "error", "message": STATUS_MESSAGES["STORAGE_FULL"]}

    # Сохранение на диск
    final_filename = f"{file_hash[:8]}_{file.filename}"
    final_path = UPLOAD_DIR / final_filename

    try:
        if not final_path.exists():
            with open(final_path, "wb") as f:
                f.write(file_bytes)
    except OSError:
        connection.close()
        write_system_log("DISK_ERROR", "Сбой файловой системы", file.filename, file_hash, STATUS_MESSAGES["SAVE_ERROR"])
        return {"status": "error", "message": STATUS_MESSAGES["SAVE_ERROR"]}

    # Запись метаданных файла в базу
    cursor.execute(
        "INSERT INTO FILESDB (Filename, Filepath, FileSize, FileType, FileHash, IsTrash) "
        "VALUES (?, ?, ?, ?, ?, 0)",
        (file.filename, str(final_path), file_size, content_type, file_hash)
    )

    # Лог успешного сохранения
    cursor.execute(
        "INSERT INTO SECURITYDB (EventType, Details, FileName, FileHash, ScanResult, AntVirCounter, TotalAntViruses) "
        "VALUES (?, ?, ?, ?, ?, 0, 0)",
        ("UPLOAD_SUCCESS", "Файл принят сервером", file.filename, file_hash, STATUS_MESSAGES["SUCCESS"])
    )

    connection.commit()
    connection.close()
    return {"status": "ok", "message": STATUS_MESSAGES["SUCCESS"]}

# Скачивание файла
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
    real_path = Path(row[1])
    media_type = row[2]

    if not real_path.exists():
        raise HTTPException(status_code=404, detail="Файл физически не найден")

    return FileResponse(
        path=str(real_path),
        filename=filename,
        media_type=media_type,
        content_disposition_type="inline"
    )

# Окончательное удаление файла
@app.delete("/api/files/{file_id}")
def deleteFile(file_id: int):
    connection = sqlite3.connect(DB_PATH, timeout=30)
    cursor = connection.cursor()
    cursor.execute("SELECT Filepath, Filename FROM FILESDB WHERE FileID = ?", (file_id,))
    row = cursor.fetchone()

    if row is None:
        connection.close()
        return {"status": "error", "message": "Файл не найден"}

    real_path = Path(row[0])
    if real_path.exists():
        try:
            real_path.unlink()
        except OSError:
            pass

    cursor.execute("DELETE FROM FILESDB WHERE FileID = ?", (file_id,))
    connection.commit()
    connection.close()
    return {"status": "ok", "message": f"Файл {row[1]} окончательно удален"}

# Журнал операций
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

    # Определение внешнего домена через заголовки прокси
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
    real_path = Path(row[2])
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