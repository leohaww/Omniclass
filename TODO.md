# TODO — CRUD Director Courses (Manajemen Mata Kuliah)

## Step 1 — Backend (app.py)
- [x] Tambahkan endpoint: 
  - [ ] `POST /director/courses/<cid>/edit` (update semua field course)
  - [ ] `POST /director/courses/<cid>/toggle` (aktif/nonaktif is_active)
  - [ ] `POST /director/courses/<cid>/delete` (hapus course)
- [ ] Pastikan akses hanya milik course milik institution director.
- [ ] Tambahkan AuditLog pada setiap aksi.
- [ ] Untuk delete: cegah jika course masih punya mahasiswa terdaftar.

## Step 2 — Frontend (templates/director/courses.html)
- [ ] Perbaiki tombol action pada card:
  - [ ] Pencil → open modal edit
  - [ ] Pause → toggle is_active (nonaktif/aktif)
  - [ ] Trash → modal konfirmasi hapus
- [ ] Tambahkan modal:
  - [ ] Modal Edit Course (form lengkap, responsive)
  - [ ] Modal Konfirmasi Hapus (mewah + jelas)
- [ ] Styling menyesuaikan tema luxury + responsive.

## Step 3 — Test
- [ ] Coba flow: create → edit → toggle → enroll/unenroll tetap aman.
- [ ] Pastikan tombol pause dan delete benar-benar memanggil endpoint backend.

