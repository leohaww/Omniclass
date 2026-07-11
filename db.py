# ═══════════════════════════════════════════════════════════════
#  OmniClass — db.py  (Database Models — Full Connected)
# ═══════════════════════════════════════════════════════════════
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import secrets

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Silakan login untuk mengakses halaman ini.'
login_manager.login_message_category = 'warning'


class Institution(db.Model):
    __tablename__ = 'institutions'
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(200), nullable=False)
    code       = db.Column(db.String(20), unique=True, nullable=False)
    type       = db.Column(db.Enum('university','school','company','other'), default='university')
    address    = db.Column(db.Text)
    phone      = db.Column(db.String(20))
    email      = db.Column(db.String(150))
    website    = db.Column(db.String(255))
    logo       = db.Column(db.String(255), default='default_logo.svg')
    is_active  = db.Column(db.Boolean, default=True)
    max_users  = db.Column(db.Integer, default=1000)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    users   = db.relationship('User',   back_populates='institution', lazy='dynamic')
    courses = db.relationship('Course', back_populates='institution', lazy='dynamic')

    @property
    def logo_url(self):
        if self.logo and self.logo.startswith('http'): return self.logo
        if self.logo: return f'/static/img/{self.logo}'
        return '/static/img/default_logo.svg'

    def __repr__(self): return f'<Institution {self.name}>'


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id             = db.Column(db.Integer, primary_key=True)
    institution_id = db.Column(db.Integer, db.ForeignKey('institutions.id'), nullable=False)
    full_name      = db.Column(db.String(150), nullable=False)
    email          = db.Column(db.String(150), unique=True, nullable=False)
    username       = db.Column(db.String(80),  unique=True, nullable=False)
    password_hash  = db.Column(db.String(256))
    role           = db.Column(db.Enum('director','lecturer','student'), nullable=False, default='student')
    program        = db.Column(db.Enum('PPL','DM'), nullable=True)
    nip_nim        = db.Column(db.String(50))
    phone          = db.Column(db.String(20))
    avatar         = db.Column(db.String(255), default='default_avatar.svg')
    is_active      = db.Column(db.Boolean, default=True)
    is_verified    = db.Column(db.Boolean, default=False)
    last_login     = db.Column(db.DateTime)
    last_ip        = db.Column(db.String(45))
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at     = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    institution   = db.relationship('Institution', back_populates='users')
    notifications = db.relationship('Notification', back_populates='user', lazy='dynamic',
                                    cascade='all, delete-orphan')
    audit_logs    = db.relationship('AuditLog', back_populates='user', lazy='dynamic',
                                    foreign_keys='AuditLog.user_id')

    def set_password(self, p):
        self.password_hash = generate_password_hash(p, method='pbkdf2:sha256')
    def check_password(self, p):
        return check_password_hash(self.password_hash, p)
    def is_director(self): return self.role == 'director'
    def is_lecturer(self): return self.role == 'lecturer'
    def is_student(self):  return self.role == 'student'

    @property
    def avatar_url(self):
        if self.avatar and self.avatar.startswith('http'): return self.avatar
        return f'/static/img/{self.avatar}'

    @property
    def program_meta(self):
        return Course.PROGRAM_META.get(self.program, Course.PROGRAM_META['PPL'])

    def __repr__(self): return f'<User {self.username} ({self.role})>'


@login_manager.user_loader
def load_user(uid): return User.query.get(int(uid))


# Many-to-many: Course ↔ Student
enrollments = db.Table('enrollments',
    db.Column('user_id',     db.Integer, db.ForeignKey('users.id'),   primary_key=True),
    db.Column('course_id',   db.Integer, db.ForeignKey('courses.id'), primary_key=True),
    db.Column('enrolled_at', db.DateTime, default=datetime.utcnow),
    db.Column('status',      db.String(20), default='active')
)


class Course(db.Model):
    __tablename__ = 'courses'
    id             = db.Column(db.Integer, primary_key=True)
    institution_id = db.Column(db.Integer, db.ForeignKey('institutions.id'), nullable=False)
    lecturer_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    program        = db.Column(db.Enum('PPL','DM'), nullable=False, default='PPL')
    code           = db.Column(db.String(20), nullable=False)
    name           = db.Column(db.String(200), nullable=False)
    description    = db.Column(db.Text)
    credits        = db.Column(db.Integer, default=3)
    semester       = db.Column(db.String(20))
    academic_year  = db.Column(db.String(10))
    room           = db.Column(db.String(50))
    capacity       = db.Column(db.Integer, default=40)
    is_active      = db.Column(db.Boolean, default=True)
    geofence_lat   = db.Column(db.Float)
    geofence_lng   = db.Column(db.Float)
    geofence_radius= db.Column(db.Integer, default=100)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at     = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    institution = db.relationship('Institution', back_populates='courses')
    lecturer    = db.relationship('User', foreign_keys=[lecturer_id])
    students    = db.relationship('User', secondary=enrollments, lazy='dynamic',
                                  primaryjoin=(enrollments.c.course_id == id),
                                  secondaryjoin=(enrollments.c.user_id == User.id))
    schedules   = db.relationship('Schedule', back_populates='course', lazy='dynamic',
                                  cascade='all, delete-orphan')
    sessions    = db.relationship('AttendanceSession', back_populates='course', lazy='dynamic',
                                  cascade='all, delete-orphan')
    attendances = db.relationship('Attendance', back_populates='course', lazy='dynamic')
    assignments = db.relationship('Assignment', back_populates='course', lazy='dynamic',
                                  cascade='all, delete-orphan')

    @property
    def student_count(self): return self.students.count()

    PROGRAM_META = {
        'PPL': {'label': 'Pengembangan Perangkat Lunak', 'short': 'PPL',
                'color': '#4f46e5', 'color2': '#7c3aed', 'icon': 'bi-code-square',
                'bg_soft': 'rgba(79,70,229,.10)'},
        'DM':  {'label': 'Digital Marketing', 'short': 'DM',
                'color': '#ea580c', 'color2': '#db2777', 'icon': 'bi-megaphone-fill',
                'bg_soft': 'rgba(234,88,12,.10)'},
    }

    @property
    def program_meta(self):
        return self.PROGRAM_META.get(self.program, self.PROGRAM_META['PPL'])

    @property
    def program_label(self): return self.program_meta['label']

    @property
    def program_color(self): return self.program_meta['color']

    def __repr__(self): return f'<Course {self.code}>'


class Schedule(db.Model):
    __tablename__ = 'schedules'
    id          = db.Column(db.Integer, primary_key=True)
    course_id   = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)
    start_time  = db.Column(db.Time, nullable=False)
    end_time    = db.Column(db.Time, nullable=False)
    room        = db.Column(db.String(50))
    is_active   = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    course      = db.relationship('Course', back_populates='schedules')
    DAYS = {0:'Senin',1:'Selasa',2:'Rabu',3:'Kamis',4:'Jumat',5:'Sabtu',6:'Minggu'}

    @property
    def day_name(self): return self.DAYS.get(self.day_of_week, '')

    @property
    def time_range(self):
        return f"{self.start_time.strftime('%H:%M')} – {self.end_time.strftime('%H:%M')}"


class AttendanceSession(db.Model):
    __tablename__ = 'attendance_sessions'
    id             = db.Column(db.Integer, primary_key=True)
    course_id      = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    lecturer_id    = db.Column(db.Integer, db.ForeignKey('users.id'),   nullable=False)
    session_date   = db.Column(db.Date, nullable=False)
    topic          = db.Column(db.String(255))
    start_time     = db.Column(db.DateTime)
    end_time       = db.Column(db.DateTime)
    qr_token       = db.Column(db.String(64), unique=True)
    qr_expires_at  = db.Column(db.DateTime)
    method         = db.Column(db.Enum('qr_code','geofence','ip_lock','manual'), default='qr_code')
    is_open        = db.Column(db.Boolean, default=True)
    meeting_number = db.Column(db.Integer, default=1)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    course   = db.relationship('Course', back_populates='sessions')
    lecturer = db.relationship('User', foreign_keys=[lecturer_id])
    records  = db.relationship('Attendance', back_populates='session', lazy='dynamic',
                                cascade='all, delete-orphan')

    def generate_qr_token(self):
        from datetime import timedelta
        self.qr_token     = secrets.token_urlsafe(32)
        self.qr_expires_at= datetime.utcnow() + timedelta(seconds=30)
        return self.qr_token

    def is_qr_valid(self):
        return bool(self.qr_expires_at and datetime.utcnow() < self.qr_expires_at)

    @property
    def present_count(self): return self.records.filter_by(status='hadir').count()
    @property
    def absent_count(self):  return self.records.filter_by(status='alfa').count()


class Attendance(db.Model):
    __tablename__ = 'attendances'
    id            = db.Column(db.Integer, primary_key=True)
    session_id    = db.Column(db.Integer, db.ForeignKey('attendance_sessions.id'), nullable=False)
    course_id     = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    student_id    = db.Column(db.Integer, db.ForeignKey('users.id'),   nullable=False)
    status        = db.Column(db.Enum('hadir','izin','sakit','alfa'), default='alfa')
    check_in_time = db.Column(db.DateTime)
    method_used   = db.Column(db.String(30))
    latitude      = db.Column(db.Float)
    longitude     = db.Column(db.Float)
    ip_address    = db.Column(db.String(45))
    notes         = db.Column(db.Text)
    verified_by   = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    session  = db.relationship('AttendanceSession', back_populates='records')
    course   = db.relationship('Course', back_populates='attendances')
    student  = db.relationship('User', foreign_keys=[student_id])
    verifier = db.relationship('User', foreign_keys=[verified_by])

    STATUS_COLORS = {'hadir':'success','izin':'warning','sakit':'info','alfa':'danger'}

    @property
    def status_color(self): return self.STATUS_COLORS.get(self.status,'secondary')


class PermitRequest(db.Model):
    __tablename__ = 'permit_requests'
    id           = db.Column(db.Integer, primary_key=True)
    student_id   = db.Column(db.Integer, db.ForeignKey('users.id'),               nullable=False)
    course_id    = db.Column(db.Integer, db.ForeignKey('courses.id'),              nullable=False)
    session_id   = db.Column(db.Integer, db.ForeignKey('attendance_sessions.id'))
    type         = db.Column(db.Enum('izin','sakit'), nullable=False)
    reason       = db.Column(db.Text, nullable=False)
    document_url = db.Column(db.String(255))
    status       = db.Column(db.Enum('pending','approved','rejected'), default='pending')
    reviewed_by  = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewed_at  = db.Column(db.DateTime)
    review_notes = db.Column(db.Text)
    request_date = db.Column(db.Date, nullable=False)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    student  = db.relationship('User',   foreign_keys=[student_id])
    course   = db.relationship('Course', foreign_keys=[course_id])
    reviewer = db.relationship('User',   foreign_keys=[reviewed_by])


class Assignment(db.Model):
    __tablename__ = 'assignments'
    id               = db.Column(db.Integer, primary_key=True)
    course_id        = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    lecturer_id      = db.Column(db.Integer, db.ForeignKey('users.id'),   nullable=False)
    title            = db.Column(db.String(255), nullable=False)
    description      = db.Column(db.Text)
    type             = db.Column(db.Enum('tugas','kuis','ujian','proyek'), default='tugas')
    max_score        = db.Column(db.Float, default=100)
    due_date         = db.Column(db.DateTime, nullable=False)
    late_penalty     = db.Column(db.Float, default=10)
    allow_late       = db.Column(db.Boolean, default=True)
    plagiarism_check = db.Column(db.Boolean, default=False)
    is_proctored     = db.Column(db.Boolean, default=False)
    is_published     = db.Column(db.Boolean, default=False)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at       = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    course      = db.relationship('Course', back_populates='assignments')
    lecturer    = db.relationship('User',   foreign_keys=[lecturer_id])
    submissions = db.relationship('Submission', back_populates='assignment', lazy='dynamic',
                                  cascade='all, delete-orphan')

    @property
    def is_overdue(self): return datetime.utcnow() > self.due_date
    @property
    def submission_count(self): return self.submissions.count()


class Submission(db.Model):
    __tablename__ = 'submissions'
    id            = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id'), nullable=False)
    student_id    = db.Column(db.Integer, db.ForeignKey('users.id'),       nullable=False)
    text_content  = db.Column(db.Text)
    file_url      = db.Column(db.String(255))
    file_name     = db.Column(db.String(255))
    file_size     = db.Column(db.Integer)
    submitted_at  = db.Column(db.DateTime, default=datetime.utcnow)
    is_late       = db.Column(db.Boolean, default=False)
    score         = db.Column(db.Float)
    feedback      = db.Column(db.Text)
    graded_at     = db.Column(db.DateTime)
    graded_by     = db.Column(db.Integer, db.ForeignKey('users.id'))
    status        = db.Column(db.Enum('submitted','graded','returned','revision'), default='submitted')
    revision_notes= db.Column(db.Text)
    revision_count= db.Column(db.Integer, default=0)
    last_revision_at = db.Column(db.DateTime)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    assignment    = db.relationship('Assignment', back_populates='submissions')
    student       = db.relationship('User', foreign_keys=[student_id])
    grader        = db.relationship('User', foreign_keys=[graded_by])

    @property
    def final_score(self):
        if self.score is None: return None
        if self.is_late and self.assignment.late_penalty > 0:
            days_late = max(1, (self.submitted_at - self.assignment.due_date).days)
            return max(0, self.score - min(self.score, self.assignment.late_penalty * days_late))
        return self.score


class Grade(db.Model):
    __tablename__ = 'grades'
    id               = db.Column(db.Integer, primary_key=True)
    course_id        = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    student_id       = db.Column(db.Integer, db.ForeignKey('users.id'),   nullable=False)
    assignment_score = db.Column(db.Float, default=0)
    quiz_score       = db.Column(db.Float, default=0)
    midterm_score    = db.Column(db.Float, default=0)
    final_score      = db.Column(db.Float, default=0)
    attendance_score = db.Column(db.Float, default=0)
    total_score      = db.Column(db.Float)
    letter_grade     = db.Column(db.String(5))
    gpa_points       = db.Column(db.Float)
    notes            = db.Column(db.Text)
    is_final         = db.Column(db.Boolean, default=False)
    updated_by       = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at       = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    course   = db.relationship('Course', foreign_keys=[course_id])
    student  = db.relationship('User',   foreign_keys=[student_id])
    updater  = db.relationship('User',   foreign_keys=[updated_by])

    GRADE_SCALE = [
        (85,'A',4.0),(80,'A-',3.7),(75,'B+',3.3),(70,'B',3.0),(65,'B-',2.7),
        (60,'C+',2.3),(55,'C',2.0),(50,'C-',1.7),(45,'D',1.0),(0,'E',0.0)
    ]

    def calculate_total(self, w=None):
        if not w:
            w = dict(assignment=.20,quiz=.15,midterm=.25,final=.30,attendance=.10)
        t = ((self.assignment_score or 0)*w['assignment']
           + (self.quiz_score or 0)*w['quiz']
           + (self.midterm_score or 0)*w['midterm']
           + (self.final_score or 0)*w['final']
           + (self.attendance_score or 0)*w['attendance'])
        self.total_score = round(t, 2)
        self._set_letter()
        return self.total_score

    def _set_letter(self):
        s = self.total_score or 0
        for th, letter, gpa in self.GRADE_SCALE:
            if s >= th:
                self.letter_grade = letter
                self.gpa_points   = gpa
                return
        self.letter_grade = 'E'; self.gpa_points = 0.0


class Notification(db.Model):
    __tablename__ = 'notifications'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title      = db.Column(db.String(255), nullable=False)
    message    = db.Column(db.Text, nullable=False)
    type       = db.Column(db.Enum('info','success','warning','danger'), default='info')
    category   = db.Column(db.String(50))
    link       = db.Column(db.String(255))
    is_read    = db.Column(db.Boolean, default=False)
    read_at    = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user       = db.relationship('User', back_populates='notifications')

    def mark_read(self):
        self.is_read = True
        self.read_at = datetime.utcnow()

    @property
    def time_ago(self):
        d = datetime.utcnow() - self.created_at
        if d.seconds < 60:   return 'Baru saja'
        if d.seconds < 3600: return f"{d.seconds//60} mnt lalu"
        if d.days < 1:       return f"{d.seconds//3600} jam lalu"
        if d.days < 30:      return f"{d.days} hari lalu"
        return self.created_at.strftime('%d %b %Y')


class Announcement(db.Model):
    __tablename__ = 'announcements'
    id             = db.Column(db.Integer, primary_key=True)
    institution_id = db.Column(db.Integer, db.ForeignKey('institutions.id'), nullable=False)
    author_id      = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id      = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)
    title          = db.Column(db.String(255), nullable=False)
    content        = db.Column(db.Text, nullable=False)
    target         = db.Column(db.Enum('all','directors','lecturers','students','course'), default='all')
    is_pinned      = db.Column(db.Boolean, default=False)
    is_published   = db.Column(db.Boolean, default=True)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    author = db.relationship('User',   foreign_keys=[author_id])
    course = db.relationship('Course', foreign_keys=[course_id])


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    institution_id = db.Column(db.Integer, db.ForeignKey('institutions.id'), nullable=True)
    action         = db.Column(db.String(100), nullable=False)
    entity_type    = db.Column(db.String(50))
    entity_id      = db.Column(db.Integer)
    ip_address     = db.Column(db.String(45))
    status         = db.Column(db.Enum('success','failed','warning'), default='success')
    message        = db.Column(db.Text)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', back_populates='audit_logs', foreign_keys=[user_id])

    @classmethod
    def log(cls, action, entity_type=None, entity_id=None,
            status='success', message=None, user_id=None, institution_id=None):
        from flask import request as req
        from flask_login import current_user
        uid, iid = user_id, institution_id
        try:
            if not uid and current_user and current_user.is_authenticated:
                uid = current_user.id; iid = current_user.institution_id
        except Exception: pass
        e = cls(user_id=uid, institution_id=iid, action=action,
                entity_type=entity_type, entity_id=entity_id,
                ip_address=req.remote_addr if req else None,
                status=status, message=message)
        db.session.add(e); return e


# ── Helper: send notification to one user ──────────────────────
def notify(user_id, title, message, ntype='info', category=None, link=None):
    n = Notification(user_id=user_id, title=title, message=message,
                     type=ntype, category=category, link=link)
    db.session.add(n)

# ── Helper: broadcast notification to many users ───────────────
def notify_many(user_ids, title, message, ntype='info', category=None, link=None):
    for uid in user_ids:
        db.session.add(Notification(user_id=uid, title=title, message=message,
                                    type=ntype, category=category, link=link))
