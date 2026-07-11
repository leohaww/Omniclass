# TODO - Fix courses.track column missing

## Step 1: Confirm DB schema
- Jalankan:
  - `SHOW COLUMNS FROM courses;`
- Pastikan ada kolom `track`.

## Step 2: Add column (jika belum ada)
- Jalankan (MySQL):
  - `ALTER TABLE courses ADD COLUMN track ENUM('PPL','DM') NOT NULL DEFAULT 'PPL';`

## Step 3: Restart aplikasi
- Restart app Flask agar model SQLAlchemy sesuai.

## Step 4: Test halaman
- Buka: `/director/dashboard` dan pastikan tidak error.

## Status
- Kolom `courses.track` sudah ditambahkan (ENUM('PPL','DM') default 'PPL').

