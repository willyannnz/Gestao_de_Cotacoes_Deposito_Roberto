import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "cotacoes.db"
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "database" / "schema.sql"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Cria as tabelas se ainda não existirem (roda toda vez que a app sobe, é seguro)."""
    conn = get_db()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    # Preserve meses já existentes e transforma os produtos cotados em sua lista inicial.
    conn.execute(
        """INSERT OR IGNORE INTO cotacao_mensal (mes_referencia)
           SELECT DISTINCT mes_referencia FROM cotacao"""
    )
    conn.execute(
        """INSERT OR IGNORE INTO cotacao_mensal_item (mes_referencia, produto_id)
           SELECT DISTINCT mes_referencia, produto_id FROM cotacao"""
    )
    conn.commit()
    conn.close()
