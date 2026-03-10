import aiosqlite


class Database:
    def __init__(self, db_file):
        self.db_file = db_file
        self.connection = None

    async def connect(self):
        if not self.connection:
            self.connection = await aiosqlite.connect(self.db_file)
            self.connection.row_factory = aiosqlite.Row
            await self.create_tables()
            await self.migrate_db()

    async def close(self):
        if self.connection:
            await self.connection.close()
            self.connection = None

    async def create_tables(self):
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                language TEXT DEFAULT 'ru',
                university TEXT DEFAULT 'urfu',
                group_id INTEGER,
                group_name TEXT,
                date_mode TEXT DEFAULT 'default',
                custom_date_start TEXT,
                custom_date_end TEXT,
                notifications_enabled INTEGER DEFAULT 0,
                notification_generation INTEGER DEFAULT 0
            )
        """)
        await self.connection.commit()

    async def migrate_db(self):
        async with self.connection.execute("PRAGMA user_version") as cursor:
            version = (await cursor.fetchone())[0]

        async with self.connection.execute("PRAGMA table_info(users)") as cursor:
            columns = [row[1] for row in await cursor.fetchall()]

        if version < 1:
            # Check existing columns to handle partial migrations from previous versions safely
            if "custom_date_start" not in columns:
                await self.connection.execute("ALTER TABLE users ADD COLUMN custom_date_start TEXT")
            if "custom_date_end" not in columns:
                await self.connection.execute("ALTER TABLE users ADD COLUMN custom_date_end TEXT")
            if "notifications_enabled" not in columns:
                await self.connection.execute("ALTER TABLE users ADD COLUMN notifications_enabled INTEGER DEFAULT 0")
            await self.connection.execute("PRAGMA user_version = 1")
            version = 1

        if version < 2:
            if "notification_generation" not in columns:
                await self.connection.execute("ALTER TABLE users ADD COLUMN notification_generation INTEGER DEFAULT 0")
            await self.connection.execute("PRAGMA user_version = 2")

        await self.connection.commit()

    async def user_exists(self, user_id):
        async with self.connection.execute("SELECT 1 FROM users WHERE user_id = ? LIMIT 1", (user_id,)) as cursor:
            result = await cursor.fetchone()
            return bool(result)

    async def add_user(self, user_id):
        await self.connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        await self.connection.commit()

    async def ensure_user(self, user_id):
        await self.connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        await self.connection.commit()

    async def get_user_settings(self, user_id):
        async with self.connection.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

    async def update_language(self, user_id, language):
        await self.connection.execute("UPDATE users SET language = ? WHERE user_id = ?", (language, user_id))
        await self.connection.commit()

    async def update_group(self, user_id, group_id, group_name):
        await self.connection.execute("UPDATE users SET group_id = ?, group_name = ? WHERE user_id = ?", (group_id, group_name, user_id))
        await self.connection.commit()

    async def update_date_mode(self, user_id, date_mode):
        await self.connection.execute("UPDATE users SET date_mode = ? WHERE user_id = ?", (date_mode, user_id))
        await self.connection.commit()

    async def update_custom_date_range(self, user_id, start_date, end_date):
        await self.connection.execute("UPDATE users SET custom_date_start = ?, custom_date_end = ?, date_mode = 'custom' WHERE user_id = ?", (start_date, end_date, user_id))
        await self.connection.commit()

    async def set_notification_status(self, user_id, status: bool):
        val = 1 if status else 0
        if status:
            await self.connection.execute(
                "UPDATE users SET notifications_enabled = ? WHERE user_id = ?",
                (val, user_id)
            )
        else:
            await self.connection.execute(
                """
                UPDATE users
                SET notifications_enabled = ?,
                    notification_generation = COALESCE(notification_generation, 0) + 1
                WHERE user_id = ?
                """,
                (val, user_id)
            )
        await self.connection.commit()

    async def get_users_with_notifications(self):
        """Returns list of users with notifications enabled and group selected"""
        async with self.connection.execute(
            """
            SELECT user_id, group_id, language, COALESCE(notification_generation, 0) AS notification_generation
            FROM users
            WHERE notifications_enabled = 1 AND group_id IS NOT NULL
            """
        ) as cursor:
            return await cursor.fetchall()

db = Database("shedul_pro.db")
