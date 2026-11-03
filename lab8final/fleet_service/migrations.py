"""Expand -> dual write -> switch reads -> contract, independently versioned SQL."""
import sqlite3
from contextlib import closing
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent / 'migrations'


def apply_migrations(db_path, up_to=4):
    """Run requested stages one at a time; history stored per Fleet database."""
    if not 0 <= up_to <= 4:
        raise ValueError('up_to must be in [0, 4]')
    with closing(sqlite3.connect(db_path)) as db, db:
        db.execute('CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, filename TEXT NOT NULL)')
        already={r[0] for r in db.execute('SELECT version FROM schema_migrations')}
        for version in range(1, up_to+1):
            if version in already:
                continue
            filename = f'{version:03d}_' + {1:'expand.sql',2:'dual_write.sql',3:'switch_reads.sql',4:'contract.sql'}[version]
            script=(MIGRATIONS_DIR/filename).read_text(encoding='utf-8')
            # The SQL script is one migration; fail instead of silently skipping.
            db.executescript(script)
            db.execute('INSERT INTO schema_migrations VALUES (?,?)',(version,filename))
        return sorted(r[0] for r in db.execute('SELECT version FROM schema_migrations'))


def schema_columns(db):
    return {row[1] for row in db.execute('PRAGMA table_info(vehicles)')}


def current_stage(db):
    try:
        row=db.execute('SELECT MAX(version) FROM schema_migrations').fetchone()
        return row[0] or 0
    except sqlite3.OperationalError:
        return 0
