import sqlite3

connection = sqlite3.connect('Top.db')
cursor = connection.cursor()

try:
    # Включаем WAL режим для быстрой и параллельной работы с БД
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Таблица файлов: хранит метаданные, пути, размер и публичные токены
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS FILESDB(
        FileID INTEGER PRIMARY KEY AUTOINCREMENT,
        Filename TEXT NOT NULL,
        Filepath TEXT NOT NULL,
        FileType TEXT NOT NULL,
        FileSize INTEGER NOT NULL,
        FileHash TEXT NOT NULL,
        IsTrash INTEGER DEFAULT 0,
        UploadDate TEXT DEFAULT CURRENT_TIMESTAMP,
        IsPublic INTEGER DEFAULT 0,
        PublicToken TEXT
    )''')

    # Настройки хранилища
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS PETSETTINGSDB(
        SettingID INTEGER PRIMARY KEY AUTOINCREMENT,
        Theme TEXT NOT NULL DEFAULT 'Dark',
        StorageLimitBytes INTEGER DEFAULT 42949672960
    )''')
    cursor.execute('''
    INSERT OR IGNORE INTO PETSETTINGSDB (SettingID, Theme, StorageLimitBytes)
    VALUES (1, 'Dark', 42949672960)
    ''')

    # Таблица безопасности: собирает логи проверок файлов через VirusTotal
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS SECURITYDB(
        LogId INTEGER PRIMARY KEY AUTOINCREMENT,
        EventType TEXT NOT NULL,
        Details TEXT NOT NULL,
        FileName TEXT NOT NULL, 
        FileHash TEXT NOT NULL,
        ScanResult TEXT NOT NULL,
        AntVirCounter INTEGER NOT NULL,
        TotalAntViruses INTEGER NOT NULL,
        Timestamp TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    connection.commit()
    print("База данных 'Top.db' успешно инициализирована")
except sqlite3.Error as E:
    print(f"Произошла ошибка при работе с SQLite: {E}")
    connection.rollback()
finally:
    connection.close()