"""
========================================================
  ENTERPRISE PORTFOLIO WEB APP
  File: app.py
  Desc: Main application entry point — Flask routes,
        middleware, auth, and blueprint registration.
========================================================
"""

import os
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, jsonify, send_from_directory,
    abort
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from db import (
    init_db, get_db,
    # User
    create_user, get_user_by_email, get_user_by_id, get_all_users, update_user, delete_user,
    # Projects
    create_project, get_all_projects, get_project_by_id, update_project, delete_project,
    # Skills
    create_skill, get_all_skills, update_skill, delete_skill,
    # Experience
    create_experience, get_all_experiences, update_experience, delete_experience,
    # Education
    create_education, get_all_educations, update_education, delete_education,
    # Certificates
    create_certificate, get_all_certificates, update_certificate, delete_certificate,
    # Contact
    create_contact_message, get_all_messages, get_unread_count, mark_message_read,
    # Audit
    log_activity, get_audit_logs,
    # Settings
    get_settings, update_setting,
    # Analytics
    log_visitor, get_visitor_stats,
    # Testimonials
    create_testimonial, get_all_testimonials, update_testimonial, delete_testimonial,
    # Services
    create_service, get_all_services, update_service, delete_service,
    # Blog
    create_blog_post, get_all_blog_posts, get_blog_post_by_slug, get_blog_post_by_id,
    update_blog_post, delete_blog_post, increment_blog_views,
)

# ─────────────────────────────────────────────
#  App Factory
# ─────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB
app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg", "gif", "webp", "pdf", "svg"}

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# ─────────────────────────────────────────────
#  Init DB (needed for Gunicorn)
# ─────────────────────────────────────────────
with app.app_context():
    init_db()

# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]


def save_upload(file, subfolder="general"):
    if file and allowed_file(file.filename):
        folder = os.path.join(app.config["UPLOAD_FOLDER"], subfolder)
        os.makedirs(folder, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{ts}_{secure_filename(file.filename)}"
        path = os.path.join(folder, filename)
        file.save(path)
        return f"uploads/{subfolder}/{filename}"
    return None


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Silakan login terlebih dahulu.", "warning")
            return redirect(url_for("auth_login"))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("auth_login"))
            if session.get("role") not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator


def log_action(action, detail=""):
    if "user_id" in session:
        log_activity(session["user_id"], action, detail, request.remote_addr, request.user_agent.string)


@app.context_processor
def inject_globals():
    settings = get_settings()
    unread = get_unread_count() if "user_id" in session else 0
    return dict(
        site_settings=settings,
        unread_messages=unread,
        current_user=get_user_by_id(session["user_id"]) if "user_id" in session else None,
        now=datetime.now(),
    )


# ─────────────────────────────────────────────
#  Visitor Analytics Middleware
# ─────────────────────────────────────────────
@app.before_request
def track_visitor():
    if not request.path.startswith("/static") and not request.path.startswith("/admin"):
        log_visitor(
            ip=request.remote_addr,
            path=request.path,
            user_agent=request.user_agent.string,
            referrer=request.referrer or ""
        )


# ─────────────────────────────────────────────
#  PUBLIC ROUTES — Portfolio
# ─────────────────────────────────────────────
@app.route("/")
def index():
    projects     = get_all_projects(featured_only=True, limit=6)
    skills       = get_all_skills()
    experiences  = get_all_experiences()
    educations   = get_all_educations()
    certificates = get_all_certificates()
    stats        = get_visitor_stats()
    settings     = get_settings()
    testimonials = get_all_testimonials(featured_only=True)
    services     = get_all_services()
    recent_posts = get_all_blog_posts(status="published", limit=3)
    return render_template(
        "index.html",
        projects=projects,
        skills=skills,
        experiences=experiences,
        educations=educations,
        certificates=certificates,
        stats=stats,
        settings=settings,
        testimonials=testimonials,
        services=services,
        recent_posts=recent_posts,
    )


@app.route("/projects")
def projects():
    category = request.args.get("category", "")
    search = request.args.get("q", "")
    all_projects = get_all_projects(category=category, search=search)
    return render_template("projects.html", projects=all_projects, category=category, search=search)


@app.route("/projects/<int:project_id>")
def project_detail(project_id):
    project = get_project_by_id(project_id)
    if not project:
        abort(404)
    return render_template("project_detail.html", project=project)


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()
        if not all([name, email, subject, message]):
            flash("Semua field wajib diisi.", "danger")
        else:
            create_contact_message(name, email, subject, message, request.remote_addr)
            flash("Pesan Anda berhasil dikirim! Kami akan segera menghubungi Anda.", "success")
            return redirect(url_for("contact"))
    return render_template("contact.html")


# ─────────────────────────────────────────────
#  AUTH ROUTES
# ─────────────────────────────────────────────
@app.route("/auth/login", methods=["GET", "POST"])
def auth_login():
    if "user_id" in session:
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        otp_code = request.form.get("otp_code", "").strip()

        user = get_user_by_email(email)
        if user and check_password_hash(user["password_hash"], password):
            # MFA check (simplified — in production: TOTP via pyotp)
            if user["mfa_enabled"]:
                stored_otp = session.get("pending_otp")
                if not stored_otp or otp_code != stored_otp:
                    # Generate and "send" OTP (console simulation)
                    otp = str(secrets.randbelow(900000) + 100000)
                    session["pending_otp"] = otp
                    session["pending_user_id"] = user["id"]
                    print(f"[MFA OTP for {email}]: {otp}")
                    flash(f"Kode OTP telah dikirim ke email Anda. (Dev mode: cek console)", "info")
                    return render_template("auth/login.html", require_otp=True, email=email)
                session.pop("pending_otp", None)
                session.pop("pending_user_id", None)

            session.permanent = True
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            session["email"] = user["email"]
            session["name"] = user["full_name"]
            log_activity(user["id"], "LOGIN", f"Login sukses dari {request.remote_addr}", request.remote_addr, request.user_agent.string)
            flash(f"Selamat datang, {user['full_name']}!", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Email atau password salah.", "danger")

    return render_template("auth/login.html", require_otp=False)


@app.route("/auth/logout")
@login_required
def auth_logout():
    log_action("LOGOUT", "User logout")
    session.clear()
    flash("Anda telah berhasil logout.", "info")
    return redirect(url_for("auth_login"))


# ─────────────────────────────────────────────
#  ADMIN ROUTES
# ─────────────────────────────────────────────
@app.route("/admin")
@login_required
def admin_dashboard():
    stats = {
        "total_projects": len(get_all_projects()),
        "total_skills": len(get_all_skills()),
        "total_messages": len(get_all_messages()),
        "unread_messages": get_unread_count(),
        "total_users": len(get_all_users()),
        "visitor_stats": get_visitor_stats(),
    }
    recent_logs = get_audit_logs(limit=10)
    recent_messages = get_all_messages(limit=5)

    # Template path fix: the actual file is under templates/admin/admin/dashboard.html
    return render_template("admin/dashboard.html", stats=stats, recent_logs=recent_logs, recent_messages=recent_messages)




# ── Projects CRUD ──────────────────────────
@app.route("/admin/projects")
@login_required
def admin_projects():
    projects = get_all_projects()
    return render_template("admin/projects.html", projects=projects)


@app.route("/admin/projects/create", methods=["GET", "POST"])
@login_required
@role_required("admin", "manager")
def admin_create_project():
    if request.method == "POST":
        image_url = ""
        if "image" in request.files:
            image_url = save_upload(request.files["image"], "projects") or ""
        data = {
            "title": request.form.get("title", ""),
            "description": request.form.get("description", ""),
            "short_desc": request.form.get("short_desc", ""),
            "tech_stack": request.form.get("tech_stack", ""),
            "category": request.form.get("category", ""),
            "demo_url": request.form.get("demo_url", ""),
            "github_url": request.form.get("github_url", ""),
            "image_url": image_url,
            "is_featured": 1 if request.form.get("is_featured") else 0,
            "status": request.form.get("status", "active"),
        }
        create_project(**data)
        log_action("CREATE_PROJECT", f"Proyek '{data['title']}' dibuat")
        flash("Proyek berhasil ditambahkan!", "success")
        return redirect(url_for("admin_projects"))
    return render_template("admin/project_form.html", project=None, action="create")


@app.route("/admin/projects/<int:pid>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin", "manager")
def admin_edit_project(pid):
    project = get_project_by_id(pid)
    if not project:
        abort(404)
    if request.method == "POST":
        image_url = project["image_url"]
        if "image" in request.files and request.files["image"].filename:
            image_url = save_upload(request.files["image"], "projects") or image_url
        data = {
            "title": request.form.get("title", ""),
            "description": request.form.get("description", ""),
            "short_desc": request.form.get("short_desc", ""),
            "tech_stack": request.form.get("tech_stack", ""),
            "category": request.form.get("category", ""),
            "demo_url": request.form.get("demo_url", ""),
            "github_url": request.form.get("github_url", ""),
            "image_url": image_url,
            "is_featured": 1 if request.form.get("is_featured") else 0,
            "status": request.form.get("status", "active"),
        }
        update_project(pid, **data)
        log_action("EDIT_PROJECT", f"Proyek ID {pid} diedit")
        flash("Proyek berhasil diperbarui!", "success")
        return redirect(url_for("admin_projects"))
    return render_template("admin/project_form.html", project=project, action="edit")


@app.route("/admin/projects/<int:pid>/delete", methods=["POST"])
@login_required
@role_required("admin")
def admin_delete_project(pid):
    delete_project(pid)
    log_action("DELETE_PROJECT", f"Proyek ID {pid} dihapus")
    flash("Proyek berhasil dihapus.", "success")
    return redirect(url_for("admin_projects"))


# ── Skills CRUD ──────────────────────────────
@app.route("/admin/skills")
@login_required
def admin_skills():
    skills = get_all_skills()
    return render_template("admin/skills.html", skills=skills)


@app.route("/admin/skills/create", methods=["POST"])
@login_required
def admin_create_skill():
    create_skill(
        name=request.form.get("name", ""),
        category=request.form.get("category", ""),
        level=int(request.form.get("level", 50)),
        icon=request.form.get("icon", ""),
    )
    log_action("CREATE_SKILL", f"Skill '{request.form.get('name')}' ditambahkan")
    flash("Skill berhasil ditambahkan!", "success")
    return redirect(url_for("admin_skills"))


@app.route("/admin/skills/<int:sid>/delete", methods=["POST"])
@login_required
@role_required("admin")
def admin_delete_skill(sid):
    delete_skill(sid)
    flash("Skill berhasil dihapus.", "success")
    return redirect(url_for("admin_skills"))


# ── Experience CRUD ──────────────────────────
@app.route("/admin/experience")
@login_required
def admin_experience():
    exps = get_all_experiences()
    return render_template("admin/experience.html", experiences=exps)


@app.route("/admin/experience/create", methods=["POST"])
@login_required
def admin_create_experience():
    create_experience(
        company=request.form.get("company", ""),
        role=request.form.get("role", ""),
        start_date=request.form.get("start_date", ""),
        end_date=request.form.get("end_date", ""),
        description=request.form.get("description", ""),
        is_current=1 if request.form.get("is_current") else 0,
        location=request.form.get("location", ""),
    )
    flash("Pengalaman berhasil ditambahkan!", "success")
    return redirect(url_for("admin_experience"))


@app.route("/admin/experience/<int:eid>/delete", methods=["POST"])
@login_required
@role_required("admin")
def admin_delete_experience(eid):
    delete_experience(eid)
    flash("Pengalaman berhasil dihapus.", "success")
    return redirect(url_for("admin_experience"))


# ── Education CRUD ───────────────────────────
@app.route("/admin/education")
@login_required
def admin_education():
    edus = get_all_educations()
    return render_template("admin/education.html", educations=edus)


@app.route("/admin/education/create", methods=["POST"])
@login_required
def admin_create_education():
    create_education(
        institution=request.form.get("institution", ""),
        degree=request.form.get("degree", ""),
        field=request.form.get("field", ""),
        start_year=request.form.get("start_year", ""),
        end_year=request.form.get("end_year", ""),
        gpa=request.form.get("gpa", ""),
        description=request.form.get("description", ""),
    )
    flash("Pendidikan berhasil ditambahkan!", "success")
    return redirect(url_for("admin_education"))


@app.route("/admin/education/<int:eid>/delete", methods=["POST"])
@login_required
@role_required("admin")
def admin_delete_education(eid):
    delete_education(eid)
    flash("Pendidikan berhasil dihapus.", "success")
    return redirect(url_for("admin_education"))


# ── Certificates CRUD ────────────────────────
@app.route("/admin/certificates")
@login_required
def admin_certificates():
    certs = get_all_certificates()
    return render_template("admin/certificates.html", certificates=certs)


@app.route("/admin/certificates/create", methods=["POST"])
@login_required
def admin_create_certificate():
    image_url = ""
    if "image" in request.files:
        image_url = save_upload(request.files["image"], "certificates") or ""
    create_certificate(
        name=request.form.get("name", ""),
        issuer=request.form.get("issuer", ""),
        issue_date=request.form.get("issue_date", ""),
        credential_id=request.form.get("credential_id", ""),
        credential_url=request.form.get("credential_url", ""),
        image_url=image_url,
    )
    flash("Sertifikat berhasil ditambahkan!", "success")
    return redirect(url_for("admin_certificates"))


@app.route("/admin/certificates/<int:cid>/delete", methods=["POST"])
@login_required
@role_required("admin")
def admin_delete_certificate(cid):
    delete_certificate(cid)
    flash("Sertifikat berhasil dihapus.", "success")
    return redirect(url_for("admin_certificates"))


# ── Messages ────────────────────────────────
@app.route("/admin/messages")
@login_required
def admin_messages():
    messages = get_all_messages()
    return render_template("admin/messages.html", messages=messages)


@app.route("/admin/messages/<int:mid>/read", methods=["POST"])
@login_required
def admin_read_message(mid):
    mark_message_read(mid)
    return redirect(url_for("admin_messages"))


# ── Users (Admin only) ───────────────────────
@app.route("/admin/users")
@login_required
@role_required("admin")
def admin_users():
    users = get_all_users()
    return render_template("admin/users.html", users=users)


@app.route("/admin/users/create", methods=["POST"])
@login_required
@role_required("admin")
def admin_create_user():
    password = request.form.get("password", secrets.token_urlsafe(12))
    create_user(
        full_name=request.form.get("full_name", ""),
        email=request.form.get("email", "").lower(),
        password_hash=generate_password_hash(password),
        role=request.form.get("role", "staff"),
        mfa_enabled=1 if request.form.get("mfa_enabled") else 0,
    )
    log_action("CREATE_USER", f"User baru '{request.form.get('email')}' dibuat")
    flash(f"User berhasil dibuat! Password sementara: {password}", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/users/<int:uid>/delete", methods=["POST"])
@login_required
@role_required("admin")
def admin_delete_user(uid):
    if uid == session["user_id"]:
        flash("Anda tidak bisa menghapus akun sendiri.", "danger")
    else:
        delete_user(uid)
        log_action("DELETE_USER", f"User ID {uid} dihapus")
        flash("User berhasil dihapus.", "success")
    return redirect(url_for("admin_users"))


# ── Audit Logs ───────────────────────────────
@app.route("/admin/audit-logs")
@login_required
@role_required("admin", "manager")
def admin_audit_logs():
    logs = get_audit_logs(limit=200)
    return render_template("admin/audit_logs.html", logs=logs)


# ── Settings ────────────────────────────────
@app.route("/admin/settings", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_settings():
    if request.method == "POST":
        for key in ["site_name", "site_tagline", "owner_name", "owner_title",
                    "owner_email", "owner_phone", "owner_location",
                    "github_url", "linkedin_url", "twitter_url", "instagram_url",
                    "tiktok_url", "upwork_url", "lynk_url",
                    "meta_description", "primary_color", "accent_color"]:
            val = request.form.get(key, "")
            update_setting(key, val)

        if "avatar" in request.files and request.files["avatar"].filename:
            avatar_path = save_upload(request.files["avatar"], "avatars")
            if avatar_path:
                update_setting("owner_avatar", avatar_path)

        log_action("UPDATE_SETTINGS", "Pengaturan situs diperbarui")
        flash("Pengaturan berhasil disimpan!", "success")
        return redirect(url_for("admin_settings"))
    return render_template("admin/settings.html")


# ── Analytics API ────────────────────────────
@app.route("/admin/analytics/data")
@login_required
def admin_analytics_data():
    stats = get_visitor_stats()
    return jsonify(stats)


# ─────────────────────────────────────────────
#  API ENDPOINTS (JSON)
# ─────────────────────────────────────────────
@app.route("/api/projects")
def api_projects():
    projects = get_all_projects()
    return jsonify([dict(p) for p in projects])


@app.route("/api/skills")
def api_skills():
    skills = get_all_skills()
    return jsonify([dict(s) for s in skills])


@app.route("/api/health")
def api_health():
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()})


# ─────────────────────────────────────────────
#  Error Handlers
# ─────────────────────────────────────────────
@app.errorhandler(403)
def forbidden(e):
    return render_template("errors/403.html"), 403


@app.errorhandler(404)
def not_found(e):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("errors/500.html"), 500

# NOTE: additional routes
# NOTE: routes below are appended after bootstrap — Flask still registers them fine

# ─────────────────────────────────────────────
#  PUBLIC — Services
# ─────────────────────────────────────────────
@app.route("/services")
def services():
    all_services = get_all_services()
    return render_template("services.html", services=all_services)


# ─────────────────────────────────────────────
#  PUBLIC — Blog
# ─────────────────────────────────────────────
@app.route("/blog")
def blog():
    category = request.args.get("category", "")
    search   = request.args.get("q", "")
    posts    = get_all_blog_posts(status="published", category=category or None, search=search or None)
    featured = get_all_blog_posts(status="published", featured_only=True, limit=1)
    return render_template("blog.html", posts=posts, featured=featured[0] if featured else None,
                           category=category, search=search)


@app.route("/blog/<slug>")
def blog_post(slug):
    post = get_blog_post_by_slug(slug)
    if not post:
        abort(404)
    increment_blog_views(slug)
    recent = get_all_blog_posts(status="published", limit=4)
    recent = [p for p in recent if p["slug"] != slug][:3]
    return render_template("blog_post.html", post=post, recent_posts=recent)


# ─────────────────────────────────────────────
#  ADMIN — Testimonials
# ─────────────────────────────────────────────
@app.route("/admin/testimonials")
@login_required
def admin_testimonials():
    testimonials = get_all_testimonials()
    return render_template("admin/testimonials.html", testimonials=testimonials)


@app.route("/admin/testimonials/create", methods=["POST"])
@login_required
def admin_create_testimonial():
    avatar_url = ""
    if "client_avatar" in request.files and request.files["client_avatar"].filename:
        avatar_url = save_upload(request.files["client_avatar"], "testimonials") or ""
    create_testimonial(
        client_name    = request.form.get("client_name", ""),
        client_title   = request.form.get("client_title", ""),
        client_company = request.form.get("client_company", ""),
        client_avatar  = avatar_url,
        rating         = int(request.form.get("rating", 5)),
        content        = request.form.get("content", ""),
        project_name   = request.form.get("project_name", ""),
        is_featured    = 1 if request.form.get("is_featured") else 0,
    )
    log_action("CREATE_TESTIMONIAL", f"Testimonial dari '{request.form.get('client_name')}' ditambahkan")
    flash("Testimonial berhasil ditambahkan!", "success")
    return redirect(url_for("admin_testimonials"))


@app.route("/admin/testimonials/<int:tid>/delete", methods=["POST"])
@login_required
@role_required("admin", "manager")
def admin_delete_testimonial(tid):
    delete_testimonial(tid)
    flash("Testimonial dihapus.", "success")
    return redirect(url_for("admin_testimonials"))


# ─────────────────────────────────────────────
#  ADMIN — Services
# ─────────────────────────────────────────────
@app.route("/admin/services")
@login_required
def admin_services():
    all_services = get_all_services()
    return render_template("admin/services.html", services=all_services)


@app.route("/admin/services/create", methods=["POST"])
@login_required
def admin_create_service():
    create_service(
        title      = request.form.get("title", ""),
        subtitle   = request.form.get("subtitle", ""),
        description= request.form.get("description", ""),
        icon       = request.form.get("icon", ""),
        price_from = request.form.get("price_from", ""),
        price_to   = request.form.get("price_to", ""),
        price_unit = request.form.get("price_unit", "project"),
        features   = request.form.get("features", ""),
        is_popular = 1 if request.form.get("is_popular") else 0,
    )
    flash("Service berhasil ditambahkan!", "success")
    return redirect(url_for("admin_services"))


@app.route("/admin/services/<int:sid>/delete", methods=["POST"])
@login_required
@role_required("admin")
def admin_delete_service(sid):
    delete_service(sid)
    flash("Service dihapus.", "success")
    return redirect(url_for("admin_services"))


# ─────────────────────────────────────────────
#  ADMIN — Blog
# ─────────────────────────────────────────────
@app.route("/admin/blog")
@login_required
def admin_blog():
    posts = get_all_blog_posts()
    return render_template("admin/blog.html", posts=posts)


@app.route("/admin/blog/create", methods=["GET", "POST"])
@login_required
def admin_create_blog():
    if request.method == "POST":
        cover_url = ""
        if "cover_image" in request.files and request.files["cover_image"].filename:
            cover_url = save_upload(request.files["cover_image"], "blog") or ""
        slug = create_blog_post(
            title      = request.form.get("title", ""),
            excerpt    = request.form.get("excerpt", ""),
            content    = request.form.get("content", ""),
            cover_image= cover_url,
            category   = request.form.get("category", "Tech"),
            tags       = request.form.get("tags", ""),
            status     = request.form.get("status", "draft"),
            read_time  = int(request.form.get("read_time", 5)),
            is_featured= 1 if request.form.get("is_featured") else 0,
        )
        log_action("CREATE_BLOG", f"Post '{request.form.get('title')}' dibuat")
        flash("Artikel berhasil diterbitkan!", "success")
        return redirect(url_for("admin_blog"))
    return render_template("admin/blog_form.html", post=None, action="create")


@app.route("/admin/blog/<int:pid>/edit", methods=["GET", "POST"])
@login_required
def admin_edit_blog(pid):
    post = get_blog_post_by_id(pid)
    if not post:
        abort(404)
    if request.method == "POST":
        cover_url = post["cover_image"]
        if "cover_image" in request.files and request.files["cover_image"].filename:
            cover_url = save_upload(request.files["cover_image"], "blog") or cover_url
        update_blog_post(pid,
            title      = request.form.get("title", ""),
            excerpt    = request.form.get("excerpt", ""),
            content    = request.form.get("content", ""),
            cover_image= cover_url,
            category   = request.form.get("category", "Tech"),
            tags       = request.form.get("tags", ""),
            status     = request.form.get("status", "draft"),
            read_time  = int(request.form.get("read_time", 5)),
            is_featured= 1 if request.form.get("is_featured") else 0,
        )
        log_action("EDIT_BLOG", f"Post ID {pid} diedit")
        flash("Artikel diperbarui!", "success")
        return redirect(url_for("admin_blog"))
    return render_template("admin/blog_form.html", post=post, action="edit")


@app.route("/admin/blog/<int:pid>/delete", methods=["POST"])
@login_required
@role_required("admin")
def admin_delete_blog(pid):
    delete_blog_post(pid)
    flash("Artikel dihapus.", "success")
    return redirect(url_for("admin_blog"))


# ─────────────────────────────────────────────
#  API — public blog posts
# ─────────────────────────────────────────────
@app.route("/api/blog")
def api_blog():
    posts = get_all_blog_posts(status="published", limit=10)
    return jsonify([dict(p) for p in posts])

# ═══════════════════════════════════════════════════════════════
#  NEW IMPORTS for Week 4 + Month 2 + Month 3
# ═══════════════════════════════════════════════════════════════
import pyotp
import qrcode
import io
import base64
import json
import smtplib
import urllib.request
import urllib.parse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from calendar import monthrange
from db import (
    check_rate_limit,
    set_availability, get_availability, delete_availability,
    save_totp_secret, get_totp_secret, verify_totp_secret, delete_totp_secret,
    get_github_cache, set_github_cache,
)

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def send_email_notification(subject, body_html, settings=None):
    """Send email via SMTP. Returns True on success."""
    if not settings:
        settings = get_settings()
    host  = settings.get("smtp_host", "")
    port  = int(settings.get("smtp_port", 587))
    user  = settings.get("smtp_user", "")
    pwd   = settings.get("smtp_pass", "")
    to    = settings.get("notify_email", "")
    if not all([host, user, pwd, to]):
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{settings.get('owner_name','Portfolio')} <{user}>"
        msg["To"]      = to
        msg.attach(MIMEText(body_html, "html"))
        with smtplib.SMTP(host, port, timeout=10) as srv:
            srv.ehlo(); srv.starttls(); srv.login(user, pwd)
            srv.sendmail(user, to, msg.as_string())
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False


def verify_recaptcha(token, settings=None):
    """Verify Google reCAPTCHA v3. Returns score (0-1) or -1 on error."""
    if not settings:
        settings = get_settings()
    secret = settings.get("recaptcha_secret_key", "")
    if not secret or not token:
        return 1.0   # skip if not configured
    try:
        data = urllib.parse.urlencode({"secret": secret, "response": token}).encode()
        req  = urllib.request.Request("https://www.google.com/recaptcha/api/siteverify",
                                       data=data)
        with urllib.request.urlopen(req, timeout=5) as r:
            result = json.loads(r.read())
        return result.get("score", 0) if result.get("success") else 0
    except Exception:
        return 1.0   # fail open if network error


def optimize_image(file_path, max_width=1200, quality=82):
    """Compress and convert uploaded image to WebP."""
    try:
        from PIL import Image as PILImage
        img = PILImage.open(file_path)
        # Convert to RGB (handles PNG transparency → white bg)
        if img.mode in ("RGBA", "P"):
            bg = PILImage.new("RGB", img.size, (10, 10, 25))
            if img.mode == "RGBA":
                bg.paste(img, mask=img.split()[3])
            else:
                bg.paste(img.convert("RGBA"), mask=img.convert("RGBA").split()[3])
            img = bg
        else:
            img = img.convert("RGB")
        # Resize if too large
        if img.width > max_width:
            ratio = max_width / img.width
            img = img.resize((max_width, int(img.height * ratio)),
                              PILImage.LANCZOS)
        # Save as WebP
        webp_path = file_path.rsplit(".", 1)[0] + ".webp"
        img.save(webp_path, "WEBP", quality=quality, method=4)
        # Remove original if different
        import os
        if webp_path != file_path and os.path.exists(file_path):
            os.remove(file_path)
        return webp_path
    except Exception as e:
        print(f"[IMG OPTIMIZE] {e}")
        return file_path   # fallback to original


# Override save_upload to auto-optimize
_orig_save_upload = save_upload
def save_upload_optimized(file, subfolder="general"):
    path = _orig_save_upload(file, subfolder)
    if path and path.lower().endswith((".jpg", ".jpeg", ".png")):
        full_path = os.path.join(app.config["UPLOAD_FOLDER"],
                                 *path.replace("uploads/", "").split("/"))
        optimized = optimize_image(full_path)
        if optimized != full_path:
            rel = "uploads/" + subfolder + "/" + os.path.basename(optimized)
            return rel
    return path
# Monkey-patch
save_upload = save_upload_optimized


# ─────────────────────────────────────────────
#  RATE LIMITING decorator
# ─────────────────────────────────────────────
def rate_limit(action, max_requests=10, window=3600):
    """Decorator: blocks if IP exceeds max_requests in window seconds."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not check_rate_limit(request.remote_addr, action, max_requests, window):
                if request.is_json:
                    return jsonify({"error": "Too many requests. Try again later."}), 429
                flash("Terlalu banyak permintaan. Coba lagi nanti.", "danger")
                return redirect(request.referrer or url_for("index"))
            return f(*args, **kwargs)
        return decorated
    return decorator


# ─────────────────────────────────────────────
#  OVERRIDE contact route  (rate limit + captcha + email)
# ─────────────────────────────────────────────
@app.route("/contact/send", methods=["POST"])
@rate_limit("contact", max_requests=5, window=3600)
def contact_send():
    settings = get_settings()
    name     = request.form.get("name", "").strip()
    email    = request.form.get("email", "").strip()
    subject  = request.form.get("subject", "").strip()
    message  = request.form.get("message", "").strip()
    token    = request.form.get("g-recaptcha-response", "")

    if not all([name, email, subject, message]):
        flash("Semua field wajib diisi.", "danger")
        return redirect(url_for("contact"))

    # reCAPTCHA check
    score = verify_recaptcha(token, settings)
    if score < 0.3:
        flash("Verifikasi gagal. Silakan coba lagi.", "danger")
        return redirect(url_for("contact"))

    create_contact_message(name, email, subject, message, request.remote_addr)

    # Email notification
    html = f"""
    <div style="font-family:sans-serif;max-width:560px;margin:0 auto;background:#0d0d1a;color:#e2e8f8;padding:2rem;border-radius:12px;border:1px solid rgba(139,92,246,.3)">
      <h2 style="color:#a78bfa;margin:0 0 1.5rem">📬 Pesan Baru dari Portfolio</h2>
      <table style="width:100%;border-collapse:collapse">
        <tr><td style="padding:.5rem 0;color:#94a3b8;width:100px">Nama</td><td style="color:#e2e8f8;font-weight:600">{name}</td></tr>
        <tr><td style="padding:.5rem 0;color:#94a3b8">Email</td><td><a href="mailto:{email}" style="color:#00f5ff">{email}</a></td></tr>
        <tr><td style="padding:.5rem 0;color:#94a3b8">Subject</td><td style="color:#e2e8f8">{subject}</td></tr>
        <tr><td style="padding:.5rem 0;color:#94a3b8;vertical-align:top">Pesan</td><td style="color:#e2e8f8;line-height:1.7">{message.replace(chr(10), '<br>')}</td></tr>
      </table>
      <div style="margin-top:1.5rem;padding-top:1rem;border-top:1px solid rgba(255,255,255,.08);font-size:.82rem;color:#475569">
        IP: {request.remote_addr} · {datetime.now().strftime('%Y-%m-%d %H:%M')}
      </div>
    </div>"""
    send_email_notification(f"[Portfolio] Pesan baru dari {name}", html, settings)

    flash("Pesan Anda berhasil dikirim! Kami akan segera menghubungi Anda.", "success")
    return redirect(url_for("contact"))


# ─────────────────────────────────────────────
#  GITHUB FEED  (public API, cached 1h)
# ─────────────────────────────────────────────
@app.route("/api/github-feed")
def api_github_feed():
    settings = get_settings()
    username = settings.get("github_username", "leohaww")
    cache_key = f"github_events_{username}"
    cached = get_github_cache(cache_key)

    # Use cache if fresh (< 60 min)
    if cached:
        from datetime import timezone
        updated = datetime.fromisoformat(cached["updated_at"])
        age = (datetime.utcnow() - updated).total_seconds()
        if age < 3600:
            return jsonify(json.loads(cached["data"]))

    try:
        url = f"https://api.github.com/users/{username}/events/public?per_page=30"
        req = urllib.request.Request(url,
              headers={"User-Agent": "PortfolioApp/1.0",
                       "Accept": "application/vnd.github.v3+json"})
        with urllib.request.urlopen(req, timeout=8) as r:
            events = json.loads(r.read())

        # Filter & simplify
        simplified = []
        for ev in events[:20]:
            repo = ev.get("repo", {}).get("name", "")
            etype = ev.get("type", "")
            payload = ev.get("payload", {})
            created = ev.get("created_at", "")[:10]

            item = {"type": etype, "repo": repo, "date": created}

            if etype == "PushEvent":
                commits = payload.get("commits", [])
                item["message"] = commits[0]["message"][:80] if commits else ""
                item["count"] = len(commits)
                item["icon"] = "fa-code-commit"
            elif etype == "CreateEvent":
                item["message"] = f"Created {payload.get('ref_type','')} {payload.get('ref','')}"
                item["icon"] = "fa-plus-circle"
            elif etype == "WatchEvent":
                item["message"] = "Starred repository"
                item["icon"] = "fa-star"
            elif etype == "ForkEvent":
                item["message"] = f"Forked to {payload.get('forkee',{}).get('full_name','')}"
                item["icon"] = "fa-code-branch"
            elif etype == "PullRequestEvent":
                pr = payload.get("pull_request", {})
                item["message"] = pr.get("title", "")[:80]
                item["icon"] = "fa-code-pull-request"
                item["action"] = payload.get("action", "")
            elif etype == "IssuesEvent":
                issue = payload.get("issue", {})
                item["message"] = issue.get("title", "")[:80]
                item["icon"] = "fa-circle-dot"
                item["action"] = payload.get("action", "")
            else:
                item["message"] = etype.replace("Event", "")
                item["icon"] = "fa-github"

            simplified.append(item)

        # Also fetch repos
        repos_url = f"https://api.github.com/users/{username}/repos?sort=updated&per_page=6"
        req2 = urllib.request.Request(repos_url,
               headers={"User-Agent": "PortfolioApp/1.0"})
        with urllib.request.urlopen(req2, timeout=8) as r2:
            repos = json.loads(r2.read())

        repos_simplified = [{
            "name": rp.get("name", ""),
            "description": rp.get("description", "") or "",
            "language": rp.get("language", "") or "",
            "stars": rp.get("stargazers_count", 0),
            "forks": rp.get("forks_count", 0),
            "url": rp.get("html_url", ""),
            "updated": rp.get("updated_at", "")[:10],
        } for rp in repos]

        result = {"events": simplified, "repos": repos_simplified, "username": username}
        set_github_cache(cache_key, result)
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e), "events": [], "repos": []}), 200


# ─────────────────────────────────────────────
#  AVAILABILITY CALENDAR
# ─────────────────────────────────────────────
@app.route("/api/availability")
def api_availability():
    year  = int(request.args.get("year",  datetime.now().year))
    month = int(request.args.get("month", datetime.now().month))
    data  = get_availability(year, month)
    return jsonify(data)


@app.route("/admin/availability")
@login_required
def admin_availability():
    year  = int(request.args.get("year",  datetime.now().year))
    month = int(request.args.get("month", datetime.now().month))
    avail = get_availability(year, month)
    return render_template("admin/availability.html",
                           avail=avail, year=year, month=month)


@app.route("/admin/availability/set", methods=["POST"])
@login_required
def admin_set_availability():
    date   = request.form.get("date", "")
    status = request.form.get("status", "available")
    note   = request.form.get("note", "")
    if date:
        set_availability(date, status, note)
        log_action("SET_AVAILABILITY", f"{date} → {status}")
    return redirect(request.referrer or url_for("admin_availability"))


@app.route("/admin/availability/delete", methods=["POST"])
@login_required
def admin_delete_availability():
    date = request.form.get("date", "")
    if date:
        delete_availability(date)
    return redirect(request.referrer or url_for("admin_availability"))


# ─────────────────────────────────────────────
#  2FA TOTP SETUP
# ─────────────────────────────────────────────
@app.route("/admin/2fa/setup")
@login_required
def admin_2fa_setup():
    uid    = session["user_id"]
    user   = get_user_by_id(uid)
    secret = pyotp.random_base32()
    save_totp_secret(uid, secret)
    totp   = pyotp.TOTP(secret)
    uri    = totp.provisioning_uri(
        name=user["email"],
        issuer_name=get_settings().get("site_name", "Portfolio")
    )
    # Generate QR code as base64 PNG
    qr_img = qrcode.make(uri)
    buf    = io.BytesIO()
    qr_img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()
    return render_template("admin/2fa_setup.html",
                           secret=secret, qr_b64=qr_b64, uri=uri)


@app.route("/admin/2fa/verify", methods=["POST"])
@login_required
def admin_2fa_verify():
    uid    = session["user_id"]
    code   = request.form.get("code", "").strip().replace(" ", "")
    record = get_totp_secret(uid)
    if not record:
        flash("Setup 2FA terlebih dahulu.", "danger")
        return redirect(url_for("admin_2fa_setup"))
    totp = pyotp.TOTP(record["secret"])
    if totp.verify(code, valid_window=1):
        verify_totp_secret(uid)
        # Enable MFA on user
        update_user(uid, mfa_enabled=1)
        log_action("2FA_ENABLED", "TOTP 2FA diaktifkan")
        flash("2FA berhasil diaktifkan! Akun Anda sekarang lebih aman.", "success")
        return redirect(url_for("admin_settings"))
    flash("Kode OTP tidak valid. Coba lagi.", "danger")
    return redirect(url_for("admin_2fa_setup"))


@app.route("/admin/2fa/disable", methods=["POST"])
@login_required
def admin_2fa_disable():
    uid = session["user_id"]
    delete_totp_secret(uid)
    update_user(uid, mfa_enabled=0)
    log_action("2FA_DISABLED", "TOTP 2FA dinonaktifkan")
    flash("2FA berhasil dinonaktifkan.", "info")
    return redirect(url_for("admin_settings"))


# ─────────────────────────────────────────────
#  PWA FILES
# ─────────────────────────────────────────────
@app.route("/manifest.json")
def pwa_manifest():
    settings = get_settings()
    manifest = {
        "name": settings.get("owner_name", "Portfolio"),
        "short_name": settings.get("owner_name", "Portfolio").split()[0],
        "description": settings.get("meta_description", ""),
        "start_url": "/",
        "display": "standalone",
        "background_color": settings.get("primary_color", "#04040f"),
        "theme_color": settings.get("pwa_theme_color", "#04040f"),
        "orientation": "portrait-primary",
        "lang": settings.get("default_lang", "id"),
        "icons": [
            {"src": "/static/img/pwa-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "/static/img/pwa-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
        "screenshots": [],
        "categories": ["portfolio", "technology"],
    }
    return jsonify(manifest), 200, {"Content-Type": "application/manifest+json"}


@app.route("/sw.js")
def service_worker():
    sw_code = """
const CACHE = 'portfolio-v2';
const STATIC = [
  '/','/static/css/main.css','/static/js/main.js',
  '/offline'
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(STATIC)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ));
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  if (e.request.url.includes('/api/')) {
    // Network first for API
    e.respondWith(
      fetch(e.request).catch(() => new Response('[]', {headers:{'Content-Type':'application/json'}}))
    );
    return;
  }
  e.respondWith(
    caches.match(e.request).then(cached => {
      const net = fetch(e.request).then(res => {
        if (res.ok) {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return res;
      });
      return cached || net.catch(() =>
        caches.match('/offline').then(r => r || new Response('Offline'))
      );
    })
  );
});
"""
    return sw_code, 200, {"Content-Type": "application/javascript",
                           "Service-Worker-Allowed": "/"}


@app.route("/offline")
def offline_page():
    return render_template("offline.html")


# ─────────────────────────────────────────────
#  MULTI-LANGUAGE  (i18n via JSON files)
# ─────────────────────────────────────────────
_translations = {}

def load_translations():
    import os, json
    global _translations
    lang_dir = os.path.join(os.path.dirname(__file__), "translations")
    os.makedirs(lang_dir, exist_ok=True)
    for lang in ["id", "en"]:
        path = os.path.join(lang_dir, f"{lang}.json")
        if os.path.exists(path):
            with open(path) as f:
                _translations[lang] = json.load(f)
        else:
            _translations[lang] = {}


def get_translation(key, lang=None):
    if not lang:
        lang = session.get("lang", get_settings().get("default_lang", "id"))
    return _translations.get(lang, {}).get(key, key)


@app.context_processor
def inject_i18n():
    lang = session.get("lang", "id")
    return dict(t=get_translation, current_lang=lang)


@app.route("/lang/<code>")
def set_language(code):
    if code in ["id", "en"]:
        session["lang"] = code
    return redirect(request.referrer or url_for("index"))


# ─────────────────────────────────────────────
#  ADMIN — Settings (extended with new fields)
# ─────────────────────────────────────────────
@app.route("/admin/settings/email-test", methods=["POST"])
@login_required
@role_required("admin")
def admin_test_email():
    settings = get_settings()
    ok = send_email_notification(
        "[Portfolio] Test Email",
        "<h2>✅ Email berhasil!</h2><p>Konfigurasi SMTP Anda bekerja dengan baik.</p>",
        settings
    )
    flash("Email test terkirim!" if ok else "Gagal kirim email. Periksa konfigurasi SMTP.", "success" if ok else "danger")
    return redirect(url_for("admin_settings"))


# ─────────────────────────────────────────────
#  ADMIN — Update settings (extended)
# ─────────────────────────────────────────────
@app.route("/admin/settings/update", methods=["POST"])
@login_required
@role_required("admin")
def admin_settings_update():
    all_keys = [
        "site_name", "site_tagline", "owner_name", "owner_title",
        "owner_email", "owner_phone", "owner_location",
        "github_url", "linkedin_url", "twitter_url", "instagram_url",
        "tiktok_url", "upwork_url", "lynk_url",
        "meta_description", "primary_color", "accent_color",
        "smtp_host", "smtp_port", "smtp_user", "smtp_pass", "notify_email",
        "github_username",
        "availability_status", "availability_msg",
        "default_lang",
        "recaptcha_site_key", "recaptcha_secret_key",
        "pwa_enabled", "pwa_theme_color",
    ]
    for key in all_keys:
        val = request.form.get(key, "")
        update_setting(key, val)

    if "avatar" in request.files and request.files["avatar"].filename:
        avatar_path = save_upload(request.files["avatar"], "avatars")
        if avatar_path:
            update_setting("owner_avatar", avatar_path)

    log_action("UPDATE_SETTINGS", "Pengaturan situs diperbarui")
    flash("Pengaturan berhasil disimpan!", "success")
    return redirect(url_for("admin_settings"))


# ─────────────────────────────────────────────────────────────
#  TAMBAHKAN ROUTE INI KE app.py
#  Letakkan sebelum:  if __name__ == "__main__":
# ─────────────────────────────────────────────────────────────

@app.route("/api/upload-media", methods=["POST"])
@login_required
def api_upload_media():
    """
    Single-file upload endpoint yang dipanggil oleh
    blog_form.html untuk setiap file dalam folder.
    Returns: { "url": "uploads/blog/filename.webp", "name": "...", "size": ... }
    """
    if "file" not in request.files:
        return jsonify({"error": "No file"}), 400

    file      = request.files["file"]
    subfolder = request.form.get("subfolder", "blog")

    if not file or not file.filename:
        return jsonify({"error": "Empty file"}), 400

    # Save + auto-optimize (WebP conversion via save_upload_optimized)
    saved_path = save_upload(file, subfolder)

    if not saved_path:
        return jsonify({"error": "Upload failed"}), 500

    return jsonify({
        "url":  url_for("static", filename=saved_path, _external=False),
        "name": file.filename,
        "path": saved_path,
        "size": request.content_length or 0,
    })
# ─────────────────────────────────────────────
#  Bootstrap
# ─────────────────────────────────────────────
if __name__ == "__main__":
    load_translations()
    # Pakai port khusus Flask supaya tidak tabrakan dengan web app lain
    # (hindari ikut-ikutan env PORT global yang mungkin milik app lain)
    port = int(os.environ.get("FLASK_PORT", 5005))
    app.run(debug=True, host="0.0.0.0", port=port)



