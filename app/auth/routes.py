from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    session,
    url_for,
    current_app
)

from app.database import db
from app.models import User
from app import mail
from flask_mail import Message
from datetime import datetime, timedelta
# Regular Expression Library
import re 
import secrets


auth = Blueprint("auth", __name__)
# HOME
@auth.route("/")
def index():

    feedbacks = [
        ("Ali", "Excellent platform for AI content.", 5),
        ("Maryam", "Humanizer works really well.", 5),
        ("Ahmed", "SEO analysis is very useful.", 4)
    ]

    return render_template(
        "user/index.html",
        feedbacks=feedbacks
    )
# LOGIN
@auth.route(
    "/login",
    methods=["GET", "POST"]
)
@auth.route("/login", methods=["GET", "POST"])
def login():

    MAX_ATTEMPTS = 5
    LOCK_MINUTES = 15

    def locked_response(user, now):
        remaining = max(
            1,
            int(
                (
                    user.login_locked_until - now
                ).total_seconds()
            ) + 1
        )

        session["login_lock_email"] = user.email

        return render_template(
            "auth/login.html",
            error="Too many incorrect attempts. Please try again when the timer ends.",
            lock_seconds=remaining,
            entered_email=user.email
        ), 429

    # On refresh, show the remaining timer for this browser.
    if request.method == "GET":
        locked_email = session.get("login_lock_email")

        if locked_email:
            locked_user = User.query.filter_by(
                email=locked_email
            ).first()

            now = datetime.utcnow()

            if (
                locked_user
                and locked_user.login_locked_until
                and locked_user.login_locked_until > now
            ):
                return locked_response(
                    locked_user,
                    now
                )

            session.pop(
                "login_lock_email",
                None
            )

        return render_template("auth/login.html")

    email = request.form.get(
        "email",
        ""
    ).strip().lower()

    password = request.form.get(
        "password",
        ""
    )

    if not email or not password:
        return render_template(
            "auth/login.html",
            error="Email and password are required.",
            entered_email=email
        ), 400

    user = User.query.filter_by(
        email=email
    ).first()

    # Same message for an unknown email and a wrong password.
    if user is None:
        return render_template(
            "auth/login.html",
            error="Invalid email or password.",
            entered_email=email
        ), 401

    now = datetime.utcnow()

    # Check active temporary lock before checking password.
    if (
        user.login_locked_until
        and user.login_locked_until > now
    ):
        return locked_response(
            user,
            now
        )

    # An expired lock starts a fresh set of attempts.
    if user.login_locked_until:
        user.login_locked_until = None
        user.failed_login_attempts = 0
        db.session.commit()
        session.pop("login_lock_email", None)
    # Timed suspension khatam ho chuki ho to account active karo.
    if (
        (user.status or "").lower() == "suspended"
        and user.suspended_until is not None
        and user.suspended_until <= datetime.utcnow()
    ):
        user.status = "active"
        user.suspended_until = None
        user.status_reason = None
        user.status_changed_at = datetime.utcnow()
        db.session.commit()
    # Check existing account moderation status.
    user_role = (
        user.role or "user"
    ).strip().lower()

    user_status = (
        user.status or "active"
    ).strip().lower()

    if (
        user_role != "admin"
        and user_status in {
            "blocked",
            "suspended",
            "pending_deletion",
            "deleted"
        }
    ):
        status_messages = {
            "blocked": (
                "Your account has been blocked by the administrator. "
                "Please contact support."
            ),
            "suspended": (
    f"Your account is temporarily suspended. "
    f"Try again in {max(1, int((user.suspended_until - datetime.utcnow()).total_seconds() / 60) + 1)} minute(s)."
    if user.suspended_until and user.suspended_until > datetime.utcnow()
    else "Your account is suspended. Please contact support."
),
            "pending_deletion": (
                "Your account is scheduled for deletion."
            ),
            "deleted": (
                "This account is no longer available."
            )
        }

        session.clear()

        return render_template(
            "auth/login.html",
            error=status_messages.get(
                user_status,
                "Your account is unavailable."
            ),
            entered_email=email
        ), 403

    # Wrong password: increment attempts in the database.
    if not user.check_password(password):
        user.failed_login_attempts = (
            user.failed_login_attempts or 0
        ) + 1

        if user.failed_login_attempts >= MAX_ATTEMPTS:
            user.login_locked_until = (
                now + timedelta(
                    minutes=LOCK_MINUTES
                )
            )

            db.session.commit()

            return locked_response(
                user,
                now
            )

        attempts_left = (
            MAX_ATTEMPTS
            - user.failed_login_attempts
        )

        db.session.commit()

        return render_template(
            "auth/login.html",
            error=(
                "Invalid email or password. "
                f"{attempts_left} attempt(s) remaining."
            ),
            entered_email=email
        ), 401

    # Correct password: reset failed attempt count.
    user.failed_login_attempts = 0
    user.login_locked_until = None
    db.session.commit()

    session.pop(
        "login_lock_email",
        None
    )

    # Existing verification flow.
    if (
        user_role != "admin"
        and not user.is_verified
    ):
        session["pending_verification_email"] = (
            user.email
        )

        return redirect(
            url_for(
                "auth.resend_verification"
            )
        )

    # Existing session and redirects.
    remember_me = request.form.get("remember") == "on"
    session.permanent = remember_me

    session["user_id"] = user.id
    session["user_name"] = user.name
    session["user_email"] = user.email
    session["role"] = user_role  

    session.pop(
        "pending_verification_email",
        None
    )

    if user_role == "admin":
        return redirect(
            url_for("admin.dashboard")
        )

    return redirect(
        url_for("user.dashboard")
    )

@auth.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "GET":

        return render_template(
            "auth/signup.html"
        )

    username = request.form.get(
        "username",
        ""
    ).strip()

    email = request.form.get(
        "email",
        ""
    ).strip().lower()
    password = request.form.get(
        "password",
        ""
    )
    confirm_password = request.form.get(
        "confirm_password",
        ""
    )
    # REQUIRED FIELDS
    if not username or not email or not password or not confirm_password:

        return render_template(
            "auth/signup.html",
            error="All fields are required."
        )
    # NAME VALIDATION

    if not re.match(
        r'^[A-Za-z0-9 ]+$',
        username
    ):
        return render_template(
            "auth/signup.html",
            error="Only letters, numbers and spaces are allowed."
        )

    if len(username) < 6:

        return render_template(
            "auth/signup.html",
            error="Full name must contain at least 6 characters."
        )

    # EMAIL VALIDATION

    email_pattern = r'^[^@]+@[^@]+\.[^@]+$'

    if not re.match(
        email_pattern,
        email
    ):

        return render_template(
            "auth/signup.html",
            error="Enter a valid email address."
        )
    # PASSWORD VALIDATION
    if len(password) < 8:
        return render_template(
            "auth/signup.html",
            error="Password must be at least 8 characters long."
        )
    if password != confirm_password:
        return render_template(
            "auth/signup.html",
            error="Passwords do not match."
        )
    # CHECK EXISTING USER
    existing_user = User.query.filter_by(
        email=email
    ).first()
    if existing_user:
        # Account pehle hi verify ho chuka hai
        if existing_user.is_verified:
            return render_template(
                "auth/signup.html",
                error=(
                    "Email is already registered. "
                    "Please login to continue."
                )
            )
        # Account bana tha, lekin OTP verify nahi hua
        session[
            "pending_verification_email"
        ] = existing_user.email
        # Naya OTP generate aur send hoga
        return redirect(
            url_for(
                "auth.resend_verification"
            )
        )
    # GENERATE OTP
    verification_code = str(
        secrets.randbelow(900000) + 100000
    )

    verification_expires = (
        datetime.now() + timedelta(minutes=10)
    )
    # CREATE USER
    new_user = User(
        name=username,
        email=email,
        role="user",
        is_verified=False,
        verification_code=verification_code,
        verification_expires=verification_expires
    )
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()
    # SAVE EMAIL IN SESSION
    session["pending_verification_email"] = email
    # SEND VERIFICATION EMAIL
    try:

        msg = Message(
            subject="PFCG - Email Verification Code",
            sender=current_app.config["MAIL_USERNAME"],
            recipients=[email]
        )

        msg.body = f"""
Hello {username},

Welcome to PFCG!

Your email verification code is:

{verification_code}

This code will expire in 10 minutes.

Please enter this code on the PFCG verification page.

If you did not create this account, you can ignore this email.

Regards,
PFCG Team
"""
        mail.send(msg)
    except Exception as e:
        print(
            "EMAIL SENDING ERROR:",
            str(e)
        )
        return render_template(
            "auth/signup.html",
            error="Account created, but verification email could not be sent. Please try again."
        )
    # GO TO VERIFICATION PAGE
    return redirect(
        url_for("auth.verify_email")
    )
# FORGOT PASSWORD
@auth.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "GET":
        return render_template("auth/forgot_password.html")
    email = request.form.get("email", "").strip().lower()
    if not email:
        return render_template(
            "auth/forgot_password.html",
            error="Please enter your email address."
        )
    user = User.query.filter_by(email=email).first()
    if user is None:
        return render_template(
            "auth/forgot_password.html",
            error="No account found with this email."
        )
    # Generate reset code
    reset_code = str(
        secrets.randbelow(900000) + 100000
    )
    user.verification_code = reset_code
    user.verification_expires = (
        datetime.now() + timedelta(minutes=10)
    )

    db.session.commit()

    # Send reset email
    try:

        msg = Message(
            subject="PFCG - Password Reset Code",
            sender=current_app.config["MAIL_USERNAME"],
            recipients=[email]
        )

        msg.body = f"""
Hello {user.name},

Your PFCG password reset code is:

{reset_code}

This code will expire in 10 minutes.

If you did not request a password reset, please ignore this email.

Regards,
PFCG Team
"""

        mail.send(msg)

    except Exception as e:

        print("PASSWORD RESET EMAIL ERROR:", str(e))

        return render_template(
            "auth/forgot_password.html",
            error="Unable to send reset email. Please try again."
        )

    session["reset_email"] = email

    return redirect(
        url_for("auth.reset_password")
    )
# RESET PASSWORD

@auth.route("/reset-password", methods=["GET", "POST"])
def reset_password():

    email = session.get("reset_email")

    if not email:
        return redirect(
            url_for("auth.forgot_password")
        )

    user = User.query.filter_by(
        email=email
    ).first()

    if user is None:
        return redirect(
            url_for("auth.forgot_password")
        )

    if request.method == "GET":
        return render_template(
            "auth/reset_password.html",
            email=email
        )

    reset_code = request.form.get(
        "reset_code",
        ""
    ).strip()

    new_password = request.form.get(
        "new_password",
        ""
    )

    confirm_password = request.form.get(
        "confirm_password",
        ""
    )

    # Check code
    if user.verification_code != reset_code:

        return render_template(
            "auth/reset_password.html",
            email=email,
            error="Invalid reset code."
        )

    # Check expiry
    if (
        user.verification_expires is None
        or datetime.now() > user.verification_expires
    ):

        return render_template(
            "auth/reset_password.html",
            email=email,
            error="Reset code has expired. Please request a new code."
        )

    # Check password length
    if len(new_password) < 8:

        return render_template(
            "auth/reset_password.html",
            email=email,
            error="Password must be at least 8 characters long."
        )

    # Check passwords
    if new_password != confirm_password:

        return render_template(
            "auth/reset_password.html",
            email=email,
            error="Passwords do not match."
        )

    # Update password
    user.set_password(new_password)

    # Clear reset code
    user.verification_code = None
    user.verification_expires = None

    db.session.commit()

    session.pop("reset_email", None)

    return redirect(
        url_for("auth.login")
    )
# VERIFY EMAIL
@auth.route(
    "/verify-email",
    methods=["GET", "POST"]
)
def verify_email():

    email = session.get(
        "pending_verification_email"
    )

    if not email:

        return redirect(
            url_for("auth.signup")
        )

    user = User.query.filter_by(
        email=email
    ).first()

    if user is None:

        session.pop(
            "pending_verification_email",
            None
        )
        return redirect(
            url_for("auth.signup")
        )
    # GET USER ROLE
    user_role = (
        user.role or "user"
    ).strip().lower()

    # ADMIN DOES NOT REQUIRE OTP
    if user_role == "admin":

        session.pop(
            "pending_verification_email",
            None
        )

        return redirect(
            url_for("auth.login")
        )

    # ==========================
    # ALREADY VERIFIED USER
    # ==========================

    if user.is_verified:

        session.pop(
            "pending_verification_email",
            None
        )

        return redirect(
            url_for("auth.login")
        )

    # ==========================
    # SHOW VERIFICATION PAGE
    # ==========================

    if request.method == "GET":

        return render_template(
            "auth/verify_email.html",
            email=email
        )

    # ==========================
    # GET OTP
    # ==========================

    entered_code = request.form.get(
        "verification_code",
        ""
    ).strip()

    if not entered_code:

        return render_template(
            "auth/verify_email.html",
            email=email,
            error=(
                "Please enter the verification code."
            )
        )

    # OTP must contain exactly 6 digits
    if (
        not entered_code.isdigit()
        or len(entered_code) != 6
    ):

        return render_template(
            "auth/verify_email.html",
            email=email,
            error=(
                "Verification code must contain "
                "exactly 6 digits."
            )
        )

    # ==========================
    # CHECK OTP
    # ==========================

    if user.verification_code != entered_code:

        return render_template(
            "auth/verify_email.html",
            email=email,
            error="Invalid verification code."
        )

    # ==========================
    # CHECK OTP EXPIRY
    # ==========================

    if (
        user.verification_expires is None
        or datetime.now()
        > user.verification_expires
    ):

        return render_template(
            "auth/verify_email.html",
            email=email,
            error=(
                "Verification code has expired. "
                "Please request a new code."
            )
        )
    # VERIFY USER
    user.is_verified = True
    user.verification_code = None
    user.verification_expires = None
    db.session.commit()
    session.pop(
        "pending_verification_email",
        None
    )
    return redirect(
        url_for("auth.login")
    )
# RESEND VERIFICATION CODE
@auth.route("/resend-verification")
def resend_verification():
    email = session.get(
        "pending_verification_email"
    )
    if not email:
        return redirect(
            url_for("auth.signup")
        )
    user = User.query.filter_by(
        email=email
    ).first()
    if user is None:
        session.pop(
            "pending_verification_email",
            None
        )
        return redirect(
            url_for("auth.signup")
        )
    # GET USER ROLE
    user_role = (
        user.role or "user"
    ).strip().lower()
    # ADMIN DOES NOT REQUIRE OTP
    if user_role == "admin":
        session.pop(
            "pending_verification_email",
            None
        )
        return redirect(
            url_for("auth.login")
        )
    # ALREADY VERIFIED USErs
    if user.is_verified:
        session.pop(
            "pending_verification_email",
            None
        )
        return redirect(
            url_for("auth.login")
        )
    # GENERATE NEW OTP
    verification_code = str(
        secrets.randbelow(900000)
        + 100000
    )
    verification_expires = (
        datetime.now()
        + timedelta(minutes=10)
    )
    user.verification_code = (
        verification_code
    )
    user.verification_expires = (
        verification_expires
    )
    db.session.commit()
    # SEND EMAIL
    try:
        msg = Message(
            subject=(
                "PFCG - New Verification Code"
            ),
            sender=current_app.config[
                "MAIL_DEFAULT_SENDER"
            ],
            recipients=[email]
        )
        msg.body = f"""
Hello {user.name},
Your new PFCG email verification code is:
{verification_code}
This code will expire in 10 minutes.
If you did not request this code, you can ignore this email.
Regards,
PFCG Team
"""
        mail.send(msg)
    except Exception as error:
        print(
            "RESEND EMAIL ERROR:",
            str(error)
        )
        return render_template(
            "auth/verify_email.html",
            email=email,
            error=(
                "Verification email could not be "
                "sent. Please try again."
            )
        )
    return redirect(
        url_for("auth.verify_email")
    )
# LOGOUT
@auth.route("/logout")
def logout():
    session.clear()
    return redirect(
        url_for("auth.login")
    )
# TERMS AND CONDITIONS
@auth.route("/terms")
def terms():
    return render_template(
        "auth/terms.html"
    )
@auth.route("/privacy-policy")
def privacy_policy():
    return render_template("auth/privacy_policy.html")