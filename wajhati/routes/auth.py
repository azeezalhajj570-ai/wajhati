import os
from urllib.parse import parse_qs, urljoin, urlparse

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from wajhati import db
from wajhati.models import User

auth_bp = Blueprint("auth", __name__)


def _get_ui_lang():
    lang = request.args.get("lang") or request.form.get("lang")
    if not lang and request.referrer:
        lang = parse_qs(urlparse(request.referrer).query).get("lang", [None])[0]
    lang = lang or "ar"
    return lang if lang in ("ar", "en") else "ar"


def _is_safe_redirect_url(target):
    if not target:
        return False
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    return redirect_url.scheme in ("http", "https") and host_url.netloc == redirect_url.netloc


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    lang = _get_ui_lang()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("جميع الحقول مطلوبة.", "danger")
            return render_template("register.html")

        if User.query.filter_by(email=email).first():
            flash("البريد الإلكتروني مسجل مسبقًا.", "warning")
            return render_template("register.html")

        admin_email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
        is_first_user = User.query.count() == 0
        user = User(name=name, email=email, is_admin=is_first_user or (admin_email and email == admin_email))
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash("تم إنشاء الحساب بنجاح. يرجى تسجيل الدخول.", "success")
        return redirect(url_for("auth.login", lang=lang))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    next_url = request.args.get("next")
    lang = _get_ui_lang()

    if current_user.is_authenticated:
        if _is_safe_redirect_url(next_url):
            return redirect(next_url)
        return redirect(url_for("main.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash("مرحبًا بعودتك.", "success")
            if _is_safe_redirect_url(next_url):
                return redirect(next_url)
            if lang in ("ar", "en"):
                return redirect(url_for("main.index", lang=lang))
            return redirect(url_for("main.index"))

        flash("بيانات الدخول غير صحيحة.", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("تم تسجيل الخروج بنجاح.", "info")
    return redirect(url_for("main.index"))
