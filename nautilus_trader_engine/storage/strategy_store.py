import psycopg2
from psycopg2 import sql

class StrategyStore:
    def __init__(self, db_params):
        self.conn = psycopg2.connect(**db_params)
        self.create_tables()

    def create_tables(self):
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS strategies (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() at time zone 'utc')
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS strategy_versions (
                    id SERIAL PRIMARY KEY,
                    strategy_id INTEGER REFERENCES strategies(id) ON DELETE CASCADE,
                    version INTEGER NOT NULL,
                    code TEXT NOT NULL,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() at time zone 'utc'),
                    UNIQUE(strategy_id, version)
                );
            """)
            self.conn.commit()

    def save_strategy(self, name, description, code):
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO strategies (name, description) VALUES (%s, %s) RETURNING id",
                (name, description)
            )
            strategy_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO strategy_versions (strategy_id, version, code) VALUES (%s, 1, %s)",
                (strategy_id, code)
            )
            self.conn.commit()
            return strategy_id

    def save_strategy_version(self, strategy_id, code):
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT MAX(version) FROM strategy_versions WHERE strategy_id = %s",
                (strategy_id,)
            )
            latest_version = cur.fetchone()[0] or 0
            new_version = latest_version + 1
            cur.execute(
                "INSERT INTO strategy_versions (strategy_id, version, code) VALUES (%s, %s, %s)",
                (strategy_id, new_version, code)
            )
            self.conn.commit()
            return new_version

    def get_strategy(self, strategy_id, version=None):
        with self.conn.cursor() as cur:
            if version:
                cur.execute(
                    "SELECT s.id, s.name, s.description, sv.version, sv.code, sv.created_at "
                    "FROM strategies s JOIN strategy_versions sv ON s.id = sv.strategy_id "
                    "WHERE s.id = %s AND sv.version = %s",
                    (strategy_id, version)
                )
            else:
                cur.execute(
                    "SELECT s.id, s.name, s.description, sv.version, sv.code, sv.created_at "
                    "FROM strategies s JOIN strategy_versions sv ON s.id = sv.strategy_id "
                    "WHERE s.id = %s ORDER BY sv.version DESC LIMIT 1",
                    (strategy_id,)
                )
            row = cur.fetchone()
            if row:
                return {
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "version": row[3],
                    "code": row[4],
                    "created_at": row[5]
                }
            return None

    def list_strategies(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, name, description, created_at FROM strategies")
            return [
                {
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "created_at": row[3]
                }
                for row in cur.fetchall()
            ]