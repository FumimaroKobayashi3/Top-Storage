import sqlite3

def init_db(db_path='Top.db'):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    try:
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA foreign_keys = ON;")

        # Таблица пользователей
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS USERSDB(
            UserID INTEGER PRIMARY KEY AUTOINCREMENT,
            Username TEXT NOT NULL UNIQUE,
            PasswordHash TEXT NOT NULL,
            CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Таблица файлов
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
            PublicToken TEXT,
            UserID INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (UserID) REFERENCES USERSDB(UserID) ON DELETE CASCADE
        )''')

        # Настройки хранилища (Реальный лимит Amvera Standard: 5 ГБ)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS PETSETTINGSDB(
            SettingID INTEGER PRIMARY KEY AUTOINCREMENT,
            Theme TEXT NOT NULL DEFAULT 'Dark',
            StorageLimitBytes INTEGER DEFAULT 5368709120
        )''')
        
        cursor.execute('''
        INSERT OR IGNORE INTO PETSETTINGSDB (SettingID, Theme, StorageLimitBytes)
        VALUES (1, 'Dark', 5368709120)
        ''')

        # Таблица логов операций
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS SECURITYDB(
            LogId INTEGER PRIMARY KEY AUTOINCREMENT,
            EventType TEXT NOT NULL,
            Details TEXT NOT NULL,
            FileName TEXT NOT NULL, 
            FileHash TEXT NOT NULL,
            StatsResult TEXT NOT NULL,
            Timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )''')

        connection.commit()
        print(f"База данных '{db_path}' успешно инициализирована")
    except sqlite3.Error as e:
        print(f"Ошибка при работе с SQLite: {e}")
        connection.rollback()
    finally:
        connection.close()

if __name__ == "__main__":
    init_db()