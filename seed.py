"""
OmniClass — seed.py (Full Connected Data)
Run: python seed.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, date, time, timedelta
from app import app
from db import (db, User, Institution, Course, enrollments,
                Schedule, AttendanceSession, Attendance,
                Assignment, Submission, Grade, Announcement,
                Notification, notify, notify_many)

with app.app_context():
    print("🌱 Membuat tabel & data demo OmniClass (Full Connected)...")

    # NOTE:
    # Pada MySQL tertentu, error 1813 (Tablespace exists) bisa muncul saat
    # menjalankan CREATE TABLE berulang/restore/import. Seed sebelumnya langsung
    # db.drop_all()+db.create_all() sehingga aplikasi langsung crash.
    # 
    # Karena Anda menginginkan "buat ulang dari nol", kita tetap drop/create,
    # tapi dibuat lebih toleran: jika drop/create gagal karena 1813, lakukan
    # reset yang lebih aman dengan cara men-defer create dan/atau skip ketika perlu.
    schema_ok = False
    try:
        db.drop_all()
        db.create_all()
        schema_ok = True
    except Exception as ex:
        msg = str(ex)
        # Jika error 1813 tablespace muncul, create_all kemungkinan gagal total,
        # jadi data insert akan ikut error ("table doesn't exist").
        # Maka: lanjut seed hanya bila skema sudah benar-benar ada.
        if '1813' in msg and 'DISCARD the tablespace' in msg:
            print(f"⚠️  Gagal db.create_all karena tablespace (1813). Akan cek apakah tabel sudah ada.\n   Detail: {msg}")
        else:
            raise

    if not schema_ok:
        # Pastikan setidaknya tabel institutions ada sebelum insert data demo.
        # Jika tidak ada, hentikan dengan pesan yang jelas.
        from sqlalchemy import text
        try:
            with db.engine.connect() as conn:
                r = conn.execute(text("SHOW TABLES LIKE 'institutions'"))
                exists = r.fetchone() is not None
            if not exists:
                raise RuntimeError("Skema tidak berhasil dibuat (institutions table tidak ada). Perbaiki MySQL 1813 lalu jalankan seed ulang.")
        except Exception as ex2:
            raise ex2





    # ── Institution ──────────────────────────────────────────────
    inst = Institution(
        name="Universitas Teknologi Nusantara", code="UTN",
        type="university", address="Jl. Pendidikan No. 1, Jakarta Selatan",
        phone="021-55501234", email="info@utn.ac.id",
        website="https://utn.ac.id", is_active=True)
    db.session.add(inst); db.session.flush()

    # ── Users ────────────────────────────────────────────────────
    director = User(institution_id=inst.id,
        full_name="Prof. Dr. Ahmad Fauzi, M.T.", email="director@demo.id",
        username="director", role="director", nip_nim="198501012010011001",
        phone="0812-1111-2222", is_active=True, is_verified=True)
    director.set_password("demo123")

    lecturer1 = User(institution_id=inst.id,
        full_name="Dr. Siti Rahayu, M.Kom.", email="dosen@demo.id",
        username="dosen", role="lecturer", nip_nim="199001012015041001",
        phone="0813-2222-3333", is_active=True, is_verified=True)
    lecturer1.set_password("demo123")

    lecturer2 = User(institution_id=inst.id,
        full_name="Budi Santoso, S.T., M.T.", email="budi@demo.id",
        username="budi_dosen", role="lecturer", nip_nim="198801012016041002",
        phone="0814-3333-4444", is_active=True, is_verified=True)
    lecturer2.set_password("demo123")

    student_data = [
        ("Rizky Pratama",    "siswa@demo.id",  "siswa",     "2021010001"),
        ("Dewi Anggraini",   "dewi@demo.id",   "dewi_s",    "2021010002"),
        ("Muhammad Faris",   "faris@demo.id",  "faris_m",   "2021010003"),
        ("Aulia Safitri",    "aulia@demo.id",  "aulia_s",   "2021010004"),
        ("Bagus Setiawan",   "bagus@demo.id",  "bagus_s",   "2021010005"),
        ("Citra Maharani",   "citra@demo.id",  "citra_m",   "2021010006"),
        ("Dimas Ramadhan",   "dimas@demo.id",  "dimas_r",   "2021010007"),
        ("Elsa Permatasari", "elsa@demo.id",   "elsa_p",    "2021010008"),
    ]
    students = []
    for name, email, uname, nim in student_data:
        s = User(institution_id=inst.id, full_name=name, email=email,
                 username=uname, role="student", nip_nim=nim,
                 is_active=True, is_verified=True)
        s.set_password("demo123"); students.append(s)

    db.session.add_all([director, lecturer1, lecturer2] + students)
    db.session.flush()

    # ── Courses (Director creates & assigns) ─────────────────────
    courses_data = [
        ("IF101","Pemrograman Web",          "HTML, CSS, JavaScript, React.",    3, lecturer1),
        ("IF202","Basis Data",               "SQL, normalisasi, optimasi query.", 3, lecturer1),
        ("IF303","Keamanan Sistem Informasi","Kriptografi & ethical hacking.",    3, lecturer2),
        ("IF404","Algoritma & Struktur Data","Rekursi, sorting, graph.",          3, lecturer2),
    ]
    courses = []
    for code, name, desc, credits, lec in courses_data:
        c = Course(institution_id=inst.id, lecturer_id=lec.id,
                   code=code, name=name, description=desc, credits=credits,
                   semester="Ganjil", academic_year="2024/2025",
                   room=f"Gedung A-{code[-3:]}", capacity=40, is_active=True)
        db.session.add(c); courses.append(c)
    db.session.flush()

    # ── Schedules ────────────────────────────────────────────────
    sch_data = [
        (courses[0], 0, time(7,30),  time(10,0)),
        (courses[0], 3, time(13,0),  time(15,30)),
        (courses[1], 1, time(8,0),   time(10,30)),
        (courses[2], 2, time(10,0),  time(12,30)),
        (courses[3], 4, time(9,0),   time(11,30)),
    ]
    for c, day, st, et in sch_data:
        db.session.add(Schedule(course_id=c.id, day_of_week=day,
            start_time=st, end_time=et, room=c.room, is_active=True))

    # ── Enrollments (Director enrolls students) ──────────────────
    # All students in courses[0] & courses[1], half in each of courses[2] & courses[3]
    for c in courses[:2]:
        for s in students:
            db.session.execute(enrollments.insert().values(
                user_id=s.id, course_id=c.id, status='active'))
    for c in courses[2:4]:
        for s in students[:4]:
            db.session.execute(enrollments.insert().values(
                user_id=s.id, course_id=c.id, status='active'))
    db.session.flush()

    # ── Attendance Sessions (by Lecturers) ───────────────────────
    today = date.today()
    for c in courses[:2]:
        for i in range(8):
            sd = today - timedelta(days=(7-i)*7)
            sess = AttendanceSession(
                course_id=c.id, lecturer_id=c.lecturer_id,
                session_date=sd, topic=f"Pertemuan {i+1}",
                method="qr_code", is_open=False, meeting_number=i+1,
                start_time=datetime.combine(sd, time(8,0)),
                end_time  =datetime.combine(sd, time(10,0)))
            db.session.add(sess); db.session.flush()

            enrolled_students = c.students.all()
            for j, s in enumerate(enrolled_students):
                # Vary attendance: some alfa
                status = "hadir" if (i+j) % 5 != 0 else ("izin" if j%3==0 else "alfa")
                db.session.add(Attendance(
                    session_id=sess.id, course_id=c.id,
                    student_id=s.id, status=status,
                    check_in_time=datetime.combine(sd, time(8,j%10)) if status=="hadir" else None,
                    method_used="qr_code" if status=="hadir" else None))

    # ── Assignments (by Lecturers) ────────────────────────────────
    asgn_data = [
        (courses[0], "Tugas 1: HTML & CSS Dasar",
         "Buat halaman web statis dengan HTML5 dan CSS3 modern.",
         "tugas", today+timedelta(days=7)),
        (courses[0], "Kuis JavaScript Fundamentals",
         "Kuis online 30 menit tentang JavaScript dasar.",
         "kuis",  today+timedelta(days=3)),
        (courses[0], "UTS: Framework Frontend",
         "Ujian Tengah Semester tentang React.js.",
         "ujian",  today+timedelta(days=21)),
        (courses[1], "Tugas ER Diagram",
         "Rancang ER Diagram untuk sistem e-commerce.",
         "tugas", today+timedelta(days=5)),
        (courses[1], "Proyek Akhir: Aplikasi CRUD",
         "Buat aplikasi CRUD lengkap dengan MySQL.",
         "proyek", today+timedelta(days=30)),
    ]
    assignments = []
    for c, title, desc, atype, due in asgn_data:
        a = Assignment(
            course_id=c.id, lecturer_id=c.lecturer_id,
            title=title, description=desc, type=atype,
            max_score=100, due_date=datetime.combine(due, time(23,59)),
            late_penalty=10, allow_late=True, is_published=True)
        db.session.add(a); assignments.append(a)
    db.session.flush()

    # ── Submissions (by Students) ─────────────────────────────────
    for a in assignments[:2]:
        for i, s in enumerate(courses[0].students.all()[:5]):
            is_late = (i == 0)  # first student submits late
            sub = Submission(
                assignment_id=a.id, student_id=s.id,
                text_content=f"Jawaban tugas dari {s.full_name}.",
                is_late=is_late,
                submitted_at=datetime.utcnow() - timedelta(hours=i*2))
            if i > 0:  # grade some
                sub.score    = 75 + (i*5 % 25)
                sub.feedback = f"Bagus! Perlu perbaikan di bagian {i}."
                sub.graded_at = datetime.utcnow()
                sub.graded_by = courses[0].lecturer_id
                sub.status   = 'graded'
            db.session.add(sub)

    # ── Grades ────────────────────────────────────────────────────
    for c in courses:
        for i, s in enumerate(c.students.all()):
            g = Grade(course_id=c.id, student_id=s.id,
                      assignment_score=75+(i*3 % 20),
                      quiz_score      =70+(i*5 % 25),
                      midterm_score   =72+(i*4 % 20),
                      final_score     =74+(i*3 % 22),
                      attendance_score=80+(i*2 % 15),
                      updated_by=director.id)
            g.calculate_total()
            db.session.add(g)

    # ── Announcements (Director → All roles) ─────────────────────
    ann_data = [
        ("📢 Selamat Datang di OmniClass!",
         "Selamat datang di semester baru 2024/2025. "
         "Pastikan semua mahasiswa sudah terdaftar di sistem dan mengecek jadwal masing-masing.",
         "all", True),
        ("⚠️ Jadwal UTS Semester Ganjil 2024/2025",
         "Ujian Tengah Semester dilaksanakan pada pekan ke-8. "
         "Semua dosen diminta menginput soal ke sistem selambatnya H-3 ujian.",
         "all", False),
        ("📚 Pengingat Upload Silabus",
         "Kepada seluruh dosen, harap segera mengupload silabus mata kuliah "
         "di menu Kelas Saya → Edit Kelas.",
         "lecturers", False),
        ("🎓 Informasi Pengisian KRS",
         "Pengisian KRS online dibuka mulai tanggal 1 – 15 setiap awal semester. "
         "Hubungi dosen wali jika ada kendala.",
         "students", False),
    ]
    for title, content, target, pinned in ann_data:
        a = Announcement(
            institution_id=inst.id, author_id=director.id,
            title=title, content=content, target=target,
            is_pinned=pinned, is_published=True)
        db.session.add(a)

    # ── Welcome Notifications (cross-role) ───────────────────────
    # Notify students about their enrolled courses
    for s in students:
        notify(s.id, '🎉 Selamat Datang di OmniClass!',
               f'Akun Anda telah dibuat. Anda terdaftar di beberapa mata kuliah. Cek Dashboard Anda.',
               'success', 'system')

    # Notify lecturers about their classes
    for lec in [lecturer1, lecturer2]:
        cs = Course.query.filter_by(lecturer_id=lec.id).all()
        notify(lec.id, f'📚 {len(cs)} Kelas Ditetapkan',
               f'Anda mengajar {len(cs)} mata kuliah semester ini. Silakan cek Kelas Saya.',
               'info', 'course')

    # Notify director
    notify(director.id, '✅ Sistem Siap Digunakan',
           f'OmniClass berhasil dikonfigurasi dengan {len(students)} mahasiswa, '
           f'2 dosen, dan {len(courses)} mata kuliah.',
           'success', 'system')

    db.session.commit()
    print("\n✅ Data demo berhasil dibuat!\n")
    print("=" * 52)
    print("  🏢 Direktur  :  director@demo.id  /  demo123")
    print("  👨‍🏫 Dosen 1   :  dosen@demo.id     /  demo123")
    print("  👨‍🏫 Dosen 2   :  budi@demo.id      /  demo123")
    print("  🎓 Mahasiswa :  siswa@demo.id      /  demo123")
    print("=" * 52)
    print(f"\n  Dibuat: {len(students)} mahasiswa, 4 kelas, 5 tugas, 8 sesi absensi")
    print(f"\n  Koneksi Data:")
    print(f"  ✅ Direktur   → Kelola users, kelas, enroll mahasiswa")
    print(f"  ✅ Dosen      → Buat sesi absensi → notif mahasiswa")
    print(f"  ✅ Dosen      → Buat tugas       → notif mahasiswa")
    print(f"  ✅ Mahasiswa  → Absen QR         → notif dosen")
    print(f"  ✅ Mahasiswa  → Kumpul tugas     → notif dosen")
    print(f"  ✅ Dosen      → Nilai tugas      → notif mahasiswa")
    print(f"  ✅ Direktur   → Umumkan          → notif semua role")
    print(f"\n🚀 python app.py  →  http://localhost:5000\n")
