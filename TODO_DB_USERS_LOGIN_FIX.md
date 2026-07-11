# TODO_DB_USERS_LOGIN_FIX

## Done
- [x] Tambah guard di `app.py` saat tabel `users` belum ada supaya halaman login tidak crash.

## Next (untuk mengatasi akar masalah)
- [ ] Pastikan konfigurasi `DB_NAME` di `.env` mengarah ke database yang benar.
- [ ] Jalankan `python app.py` sekali untuk memicu `db.create_all()` + `ensure_schema()`.
- [ ] Jika tetap gagal, jalankan `seed.py` / migration manual.
- [ ] Verifikasi tabel: `users`, `institutions`, `courses`, dst.

## Catatan
Error yang muncul sebelumnya:
- `sqlalchemy.exc.ProgrammingError: (1146, "Table 'omniclass_db.users' doesn't exist")`

