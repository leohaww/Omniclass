"""OmniClass — init_db.py

Dipakai untuk:
1) Memastikan database MySQL (DB_NAME) ada.
2) Membuat tabel (db.create_all).
3) Menjalankan ensure_schema() (migration ringan) agar kolom/enum baru ada.
4) Menjalankan seeder demo (seed) jika diperlukan.

Catatan penting:
- File ini sengaja dibuat terpisah agar app.py tetap clean.
- init_db() dibuat bisa dipanggil global dari app.py maupun dari script lain.
- Untuk produksi + gunicorn, sebaiknya init hanya jalan sekali.
  Gunakan argumen force=False dan/tambah ENV flag misalnya OMNICLASS_SEED=1.
"""

from __future__ import annotations

import os
from typing import Optional


def _get_db_config():
    return {
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "name": os.getenv("DB_NAME", "omniclass_db"),
    }


def ensure_mysql_database_exists() -> None:
    """Create MySQL database if it doesn't exist."""
    import pymysql

    cfg = _get_db_config()

    # connect without selecting target db
    conn = pymysql.connect(
        host=cfg["host"],
        user=cfg["user"],
        password=cfg["password"],
        port=cfg["port"],
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME=%s",
                (cfg["name"],),
            )
            exists = cur.fetchone() is not None
            if not exists:
                cur.execute(
                    f"CREATE DATABASE `{cfg['name']}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
                print(f"✅ MySQL database created: {cfg['name']}")
    finally:
        conn.close()


def init_db(
    *,
    seed_demo: Optional[bool] = None,
    force_schema: bool = False,
    seed_if_missing: bool = True,
) -> None:
    """Initialize DB: database + tables + schema + optional seeding.

    Args:
        seed_demo:
            - None: mengikuti OMNICLASS_SEED (default False)
            - True/False: override flag
        force_schema:
            Kalau True, jalankan ensure_schema() (jika ada) meskipun gagal sebelumnya.
        seed_if_missing:
            Jika True dan seed_demo True, seeder akan dieksekusi hanya jika tabel
            kosong/ belum ada data (heuristik).
    """

    from app import app  # import di dalam agar aman dari circular import
    from db import db, Institution

    # Import ensure_schema from app.py (existing implementation)
    # Jika Anda pindahkan ensure_schema ke tempat lain di masa depan, cukup update sini.
    from app import ensure_schema as _ensure_schema  # type: ignore

    ensure_mysql_database_exists()

    with app.app_context():
        db.create_all()

        if force_schema:
            _ensure_schema()
        else:
            try:
                _ensure_schema()
            except Exception as e:
                # non-fatal: schema checks shouldn't crash production
                print(f"⚠️ ensure_schema failed (non-fatal): {e}")

        # Decide seeding
        if seed_demo is None:
            seed_env = os.getenv("OMNICLASS_SEED", "0").strip().lower()
            seed_demo = seed_env in {"1", "true", "yes", "y", "on"}

        if not seed_demo:
            return

        if seed_if_missing:
            # heuristic: if institutions already exist, don't reseed
            if Institution.query.first() is not None:
                print("ℹ️ Seeder skipped: institutions already exist.")
                return

        # Run seeder demo via seed.py (existing script)
        import importlib

        # Jalankan seed.py sebagai modul; seed.py sendiri mengeksekusi saat diimport.
        # Untuk menghindari double seeding di beberapa worker, gunakan OMNICLASS_SEED=1 hanya sekali.
        importlib.import_module("seed")
        print("🌱 Seeder executed.")

