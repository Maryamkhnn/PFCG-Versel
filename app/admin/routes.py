
from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    session,
    request,
    jsonify
)
from datetime import timedelta
from secrets import token_urlsafe, compare_digest

from app.user.services.automatic_moderation_service import (
    ModerationReviewError,
    review_moderation_case,
)
from flask import request
from sqlalchemy.exc import IntegrityError
import re
from flask import current_app
from sqlalchemy import text
import math
from app.models import User
from app.database import db
from app.admin.services import (
    get_dashboard_data,
    get_users,
    get_user_activity_counts,
    get_generated_content,
    get_seo_reports,
    get_feedback,
    get_reports_data,
    get_user_by_id,
    update_user,
    delete_user,
    get_content_by_id,
    delete_content,
    get_admin_logs,
    add_admin_log,
    get_admin_settings,
    mark_feedback_reviewed,
    update_admin_settings,
   
)
# =====================================================
# ADMIN BLUEPRINT
# =====================================================

admin = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin"
)

# =====================================================
# ADMIN AUTH CHECK
# =====================================================

def admin_required():

    role = session.get("role", "")

    return (
        isinstance(role, str)
        and role.strip().lower() == "admin"
    )

# =====================================================
# DASHBOARD
# =====================================================

@admin.route("/dashboard")
def dashboard():

    if not admin_required():
        return redirect(url_for("auth.login"))

    data = get_dashboard_data()

    return render_template(
        "admin/admin_dashboard.html",
        **data
    )


@admin.route("/users")
def users():

    if not admin_required():
        return redirect(url_for("auth.login"))

    page = request.args.get(
        "page",
        1,
        type=int
    )

    if page < 1:
        page = 1

    pagination = get_users(
        page=page,
        per_page=10
    )

    user_activities = {}

    for user in pagination.items:

        user_activities[user.id] = get_user_activity_counts(
            user.id,
            user.email
        )

    return render_template(
        "admin/admin_users.html",
        users=pagination.items,
        pagination=pagination,
        user_activities=user_activities
    )
# =====================================================
# VIEW SINGLE USER
# =====================================================

@admin.route("/users/<int:user_id>", methods=["GET"])
def view_user(user_id):

    if not admin_required():
        return jsonify({
            "success": False,
            "message": "Unauthorized access."
        }), 401

    user = get_user_by_id(user_id)

    if not user:
        return jsonify({
            "success": False,
            "message": "User not found."
        }), 404

    return jsonify({
        "success": True,
        "user": {
            "id": user.id,
            "name": user.name or "",
            "username": user.username or "",
            "email": user.email or "",
            
            "role": user.role or "",
            "status": user.status or "active"
        }
    })
# =====================================================
# EDIT BASIC USER DETAILS
# =====================================================

@admin.route("/users/<int:user_id>/edit", methods=["POST"])
def edit_user(user_id):
    try:
        if not moderation_admin_allowed():
            return jsonify({
                "success": False,
                "message": "Administrator access is required."
            }), 403

        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({
                "success": False,
                "message": "Valid user details are required."
            }), 400

        name = data.get("name")

        if not isinstance(name, str) or not name.strip():
            return jsonify({
                "success": False,
                "message": "Name is required."
            }), 400

        name = name.strip()

        if len(name) > 100:
            return jsonify({
                "success": False,
                "message": "Name must not exceed 100 characters."
            }), 400

        if "username" in data:
            username = data["username"]

            if not isinstance(username, str):
                return jsonify({
                    "success": False,
                    "message": "Username must be text."
                }), 400

            username = username.strip()

            if username and not 3 <= len(username) <= 100:
                return jsonify({
                    "success": False,
                    "message": (
                        "Username must contain 3 to 100 characters, "
                        "or be left empty."
                    )
                }), 400

        user = (
            User.query
            .filter_by(id=user_id)
            .populate_existing()
            .with_for_update()
            .first()
        )

        if user is None:
            db.session.rollback()

            return jsonify({
                "success": False,
                "message": "User not found."
            }), 404

        if (user.role or "user").strip().lower() == "admin":
            db.session.rollback()

            return jsonify({
                "success": False,
                "message": "Update administrator details through My Account."
            }), 403

        if "email" in data:
            email = data["email"]

            if (
                not isinstance(email, str)
                or email.strip().lower()
                    != (user.email or "").strip().lower()
            ):
                db.session.rollback()

                return jsonify({
                    "success": False,
                    "message": "Verified email cannot be changed here."
                }), 400

        if "username" not in data:
            username = user.username

        if username:
            existing = User.query.filter(
                User.username == username,
                User.id != user.id
            ).first()

            if existing:
                db.session.rollback()

                return jsonify({
                    "success": False,
                    "message": "Username is already taken."
                }), 409

        # Preserve email, role and all moderation fields.
        user.name = name
        user.username = username or None

        db.session.execute(
            text("""
                INSERT INTO admin_logs (
                    admin_id,
                    admin_email,
                    action,
                    target_type,
                    target_details,
                    created_at
                )
                VALUES (
                    :admin_id,
                    :admin_email,
                    'Updated User',
                    'User',
                    :details,
                    UTC_TIMESTAMP()
                )
            """),
            {
                "admin_id": session["user_id"],
                "admin_email": session.get("user_email"),
                "details": (
                    f"User #{user.id}; Email: {user.email}; "
                    "Updated basic profile details."
                )
            }
        )

        profile = {
            "id": user.id,
            "name": user.name,
            "username": user.username or "",
            "email": user.email or ""
        }

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "User details updated successfully.",
            "user": profile
        })

    except IntegrityError:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "Details could not be saved. "
                       "The username may already be taken."
        }), 409

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Unable to update user details")

        return jsonify({
            "success": False,
            "message": "Unable to update this user."
        }), 500
# =====================================================
# DISABLED MANUAL ACCOUNT ACTIONS
# =====================================================

def manual_account_action_disabled():
    if not admin_required():
        return jsonify({
            "success": False,
            "message": "Administrator access is required."
        }), 403

    return jsonify({
        "success": False,
        "message": (
            "Manual account actions are disabled. "
            "Use Content Moderation to review automatic suspensions."
        )
    }), 403


@admin.route(
    "/users/<int:user_id>/toggle-block",
    methods=["POST"]
)
def toggle_block_user(user_id):
    return manual_account_action_disabled()


@admin.route(
    "/users/<int:user_id>/moderate",
    methods=["POST"]
)
def moderate_user(user_id):
    return manual_account_action_disabled()


@admin.route(
    "/users/<int:user_id>/delete",
    methods=["POST"]
)
def remove_user(user_id):
    return manual_account_action_disabled()
# =====================================================
# GENERATED CONTENT
# =====================================================

@admin.route("/content")
def content():

    if not admin_required():
        return redirect(url_for("auth.login"))

    page = request.args.get(
        "page",
        1,
        type=int
    )

    if page < 1:
        page = 1

    per_page = 10

    generated_content, total_content = get_generated_content(
        page=page,
        per_page=per_page
    )

    total_pages = (
        (total_content + per_page - 1) // per_page
        if total_content > 0
        else 1
    )

    if page > total_pages:

        return redirect(
            url_for(
                "admin.content",
                page=total_pages
            )
        )

    return render_template(
        "admin/admin_generatedcontent.html",

        generated_content=generated_content,

        total_content=total_content,

        current_page=page,

        per_page=per_page,

        total_pages=total_pages
    )


# =====================================================
# VIEW SINGLE GENERATED CONTENT
# =====================================================

@admin.route(
    "/content/<int:content_id>",
    methods=["GET"]
)
def view_content(content_id):

    if not admin_required():
        return jsonify({
            "success": False,
            "message": "Unauthorized access."
        }), 401

    content = get_content_by_id(
        content_id
    )

    if not content:
        return jsonify({
            "success": False,
            "message": "Content not found."
        }), 404

    return jsonify({
        "success": True,

        "content": {

            "id": content["id"],

            "user_email": content["user_email"],

            "topic": content["topic"],

            "content": content["content"],

            "word_count": content["word_count"],

            "content_type": content["content_type"],

            "created_at": str(
                content["created_at"]
            )
        }
    })


# =====================================================
# DELETE GENERATED CONTENT
# =====================================================

@admin.route(
    "/content/<int:content_id>/delete",
    methods=["POST"]
)
def delete_content_route(content_id):

    if not admin_required():

        return jsonify({
            "success": False,
            "message": "Unauthorized access."
        }), 401


    try:

        # ---------------------------------------------
        # GET CONTENT BEFORE DELETE
        # ---------------------------------------------

        content = get_content_by_id(
            content_id
        )


        if not content:

            return jsonify({
                "success": False,
                "message": "Generated content not found."
            }), 404


        # Save useful information before deletion

        topic = (
            content["topic"]
            or
            f"Content ID: {content_id}"
        )


        user_email = (
            content["user_email"]
            or
            "Unknown User"
        )


        content_details = (
            f"{topic} ({user_email})"
        )


        # ---------------------------------------------
        # DELETE CONTENT
        # ---------------------------------------------

        deleted = delete_content(
            content_id
        )


        if not deleted:

            return jsonify({
                "success": False,
                "message": "Generated content not found."
            }), 404


        # ---------------------------------------------
        # SAVE ADMIN ACTIVITY
        # ---------------------------------------------

        add_admin_log(

            admin_id=session.get(
                "user_id"
            ),

            admin_email=session.get(
                "user_email"
            ),

            action="Deleted Content",

            target_type="Generated Content",

            target_details=content_details

        )


        return jsonify({
            "success": True,
            "message": "Generated content deleted successfully."
        })


    except Exception as e:

        db.session.rollback()

        print(
            "DELETE CONTENT ERROR:",
            e
        )

        return jsonify({
            "success": False,
            "message": "Unable to delete generated content."
        }), 500
# =====================================================
# SEO REPORTS
# =====================================================

@admin.route("/seo")
def seo():

    if not admin_required():
        return redirect(url_for("auth.login"))

    seo_reports = get_seo_reports()

    return render_template(
        "admin/seo.html",
        seo_reports=seo_reports
    )


# =====================================================
# FEEDBACK
# =====================================================

@admin.route("/feedback")
def feedback():

    if not admin_required():
        return redirect(url_for("auth.login"))

    feedbacks = get_feedback()

    return render_template(
        "admin/admin_feedback.html",
        feedbacks=feedbacks
    )
# =====================================================
# REVIEW FEEDBACK API
# =====================================================

@admin.route(
    "/feedback/<int:feedback_id>/review",
    methods=["POST"]
)
def review_feedback(feedback_id):

    if not admin_required():

        return jsonify({
            "success": False,
            "message": "Admin login required."
        }), 401

    try:

        updated = mark_feedback_reviewed(
            feedback_id
        )

        if not updated:

            return jsonify({
                "success": False,
                "message": "Feedback not found."
            }), 404

        return jsonify({
            "success": True,
            "status": "Reviewed"
        })

    except Exception as error:

        print(
            "REVIEW FEEDBACK ERROR:",
            error
        )

        return jsonify({
            "success": False,
            "message": (
                "Unable to update feedback."
            )
        }), 500

# =====================================================
# REPORTS
# =====================================================


@admin.route("/reports")
def reports():

    if not admin_required():
        return redirect(url_for("auth.login"))

    data = get_reports_data()


    return render_template(
        "admin/admin_reports.html",
        **data
    )

# =====================================================
# ACTIVITY LOGS
# =====================================================

@admin.route("/activity-logs")
def activity_logs():

    if not admin_required():

        return redirect(
            url_for("auth.login")
        )

    logs = get_admin_logs()

    return render_template(
        "admin/admin_activity_logs.html",
        logs=logs
    )

# =====================================================
# MY ACCOUNT PAGE
# =====================================================

@admin.route("/account")
def account():
    if not admin_required():
        return redirect(url_for("auth.login"))

    admin_user = db.session.get(
        User,
        session.get("user_id")
    )

    if admin_user is None:
        session.clear()
        return redirect(url_for("auth.login"))

    settings_data = get_admin_settings()

    return render_template(
        "admin/admin_account.html",
        admin_user=admin_user,
        settings=settings_data
    )
@admin.route("/settings/update", methods=["POST"])
def update_settings():
    if not admin_required():
        return jsonify({
            "success": False,
            "message": "Unauthorized access."
        }), 401

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "message": "Valid JSON data is required."
        }), 400

    site_name = data.get("site_name")

    if not isinstance(site_name, str) or not site_name.strip():
        return jsonify({
            "success": False,
            "message": "Site name is required."
        }), 400

    site_name = site_name.strip()

    if len(site_name) > 100:
        return jsonify({
            "success": False,
            "message": "Site name must not exceed 100 characters."
        }), 400

    raw_limit = data.get("default_word_limit")

    if (
        isinstance(raw_limit, bool)
        or not isinstance(raw_limit, (int, str))
    ):
        return jsonify({
            "success": False,
            "message": "Default word limit must be a whole number."
        }), 400

    try:
        default_word_limit = int(raw_limit)
    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "Default word limit must be a whole number."
        }), 400

    if not 100 <= default_word_limit <= 5000:
        return jsonify({
            "success": False,
            "message": "Default word limit must be between 100 and 5000."
        }), 400

    try:
        update_admin_settings({
            "site_name": site_name,
            "default_word_limit": default_word_limit
        })

        add_admin_log(
            admin_id=session.get("user_id"),
            admin_email=session.get("user_email"),
            action="Updated Settings",
            target_type="System Settings",
            target_details="Administrator updated system settings."
        )

        return jsonify({
            "success": True,
            "message": "Settings saved successfully."
        })

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Unable to save admin settings")

        return jsonify({
            "success": False,
            "message": "Unable to save settings."
        }), 500
# =====================================================
# UPDATE ADMIN PROFILE
# =====================================================

@admin.route(
    "/profile/update",
    methods=["POST"]
)
def update_profile():

    if not admin_required():

        return jsonify({
            "success": False,
            "message": "Unauthorized access."
        }), 401


    # Get logged-in user ID
    user_id = session.get(
        "user_id"
    )


    if not user_id:

        return jsonify({
            "success": False,
            "message": "Session expired. Please login again."
        }), 401


    # Get user
    user = User.query.get(
        user_id
    )


    if not user:

        return jsonify({
            "success": False,
            "message": "User account not found."
        }), 404


    # Check admin role
    if (
        not user.role
        or user.role.strip().lower() != "admin"
    ):

        return jsonify({
            "success": False,
            "message": "Unauthorized account."
        }), 403


    # Get JSON data
    data = request.get_json(
        silent=True
    )


    if not data:

        return jsonify({
            "success": False,
            "message": "No data received."
        }), 400


    name = data.get(
        "name",
        ""
    ).strip()


    email = data.get(
        "email",
        ""
    ).strip().lower()


    # =================================================
    # VALIDATION
    # =================================================

    if not name or not email:

        return jsonify({
            "success": False,
            "message": "Name and email are required."
        }), 400


    if len(name) < 3:

        return jsonify({
            "success": False,
            "message": "Name must contain at least 3 characters."
        }), 400


    email_pattern = (
        r'^[^@]+@[^@]+\.[^@]+$'
    )


    if not re.match(
        email_pattern,
        email
    ):

        return jsonify({
            "success": False,
            "message": "Enter a valid email address."
        }), 400


    # =================================================
    # CHECK DUPLICATE EMAIL
    # =================================================

    existing_user = User.query.filter(
        User.email == email,
        User.id != user.id
    ).first()


    if existing_user:

        return jsonify({
            "success": False,
            "message": "This email is already registered."
        }), 400


    # =================================================
    # UPDATE DATABASE
    # =================================================

    try:

        user.name = name

        user.email = email

        db.session.commit()


        # Update session
        session["user_name"] = user.name

        session["user_email"] = user.email


        return jsonify({
            "success": True,
            "message": "Profile updated successfully."
        })


    except Exception as e:

        db.session.rollback()

        print(
            "UPDATE ADMIN PROFILE ERROR:",
            e
        )

        return jsonify({
            "success": False,
            "message": "Unable to update profile."
        }), 500

@admin.route("/blocked-attempts")
def blocked_attempts():
    if not admin_required():
        return redirect(url_for("auth.login"))

    return redirect(url_for(
        "admin.content_moderation",
        tab="attempts",
        email=request.args.get("email", ""),
        search=request.args.get("search", ""),
        page=request.args.get("page", 1, type=int) or 1
    ))

@admin.route(
    "/profile/change-password",
    methods=["POST"]
)
def change_password():

    if not admin_required():

        return jsonify({
            "success": False,
            "message": "Unauthorized access."
        }), 401


    # Get logged-in user ID
    user_id = session.get(
        "user_id"
    )


    if not user_id:

        return jsonify({
            "success": False,
            "message": "Session expired. Please login again."
        }), 401


    # Get user from users table
    user = User.query.get(
        user_id
    )


    if not user:

        return jsonify({
            "success": False,
            "message": "User account not found."
        }), 404


    # Check admin role
    if (
        not user.role
        or user.role.strip().lower() != "admin"
    ):

        return jsonify({
            "success": False,
            "message": "Unauthorized account."
        }), 403


    # =================================================
    # GET PASSWORD DATA
    # =================================================

    current_password = request.form.get(
        "current_password",
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


    # =================================================
    # REQUIRED FIELDS
    # =================================================

    if (
        not current_password
        or not new_password
        or not confirm_password
    ):

        return jsonify({
            "success": False,
            "message": "All password fields are required."
        }), 400


    # =================================================
    # CHECK CURRENT PASSWORD
    # =================================================

    if not user.check_password(
        current_password
    ):

        return jsonify({
            "success": False,
            "message": "Current password is incorrect."
        }), 400


    # =================================================
    # PASSWORD LENGTH
    # =================================================

    if len(new_password) < 8:

        return jsonify({
            "success": False,
            "message": "New password must be at least 8 characters long."
        }), 400


    # =================================================
    # CONFIRM PASSWORD
    # =================================================

    if new_password != confirm_password:

        return jsonify({
            "success": False,
            "message": "New passwords do not match."
        }), 400


    # =================================================
    # SAME PASSWORD CHECK
    # =================================================

    if current_password == new_password:

        return jsonify({
            "success": False,
            "message": "New password must be different from current password."
        }), 400


    # =================================================
    # SAVE NEW PASSWORD
    # =================================================

    try:

        user.set_password(
            new_password
        )

        db.session.commit()


        return jsonify({
            "success": True,
            "message": "Password changed successfully."
        })


    except Exception as e:

        db.session.rollback()

        print(
            "CHANGE PASSWORD ERROR:",
            e
        )

        return jsonify({
            "success": False,
            "message": "Unable to change password."
        }), 500


# =====================================================
# ADMIN LOGOUT
# =====================================================

@admin.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("auth.login")
    )

# =====================================================
# CONTENT MODERATION — SHARED PAGE
# =====================================================

@admin.route("/content-moderation", methods=["GET"])
def content_moderation():
    if not admin_required():
        return redirect(url_for("auth.login"))

    tab = request.args.get("tab", "reviews")
    if tab not in {"reviews", "attempts"}:
        tab = "reviews"

    search = request.args.get("search", "").strip()[:200]
    selected_email = request.args.get("email", "").strip().lower()

    page = max(1, request.args.get("page", 1, type=int) or 1)
    per_page = 10

    params = {
        "email": selected_email,
        "search": search,
        "pattern": f"%{search}%"
    }

    cases = []
    attempts = []
    total_attempts = 0
    total_users = 0

    if tab == "reviews":
        filters = """
            WHERE c.pending = 1
              AND (:email = '' OR LOWER(u.email) = :email)
              AND (
                  :search = ''
                  OR u.name LIKE :pattern
                  OR u.email LIKE :pattern
                  OR u.status_reason LIKE :pattern
              )
        """

        total_records = db.session.execute(
            text(f"""
                SELECT COUNT(*)
                FROM moderation_review_cases AS c
                JOIN users AS u ON u.id = c.user_id
                {filters}
            """),
            params
        ).scalar() or 0

        total_pages = max(1, math.ceil(total_records / per_page))
        page = min(page, total_pages)

        cases = db.session.execute(
            text(f"""
                SELECT
                    c.id AS case_id,
                    c.user_id,
                    c.restriction_count,
                    c.flagged_at,
                    u.name,
                    u.email,
                    u.status,
                    u.status_reason,
                    u.suspended_until
                FROM moderation_review_cases AS c
                JOIN users AS u ON u.id = c.user_id
                {filters}
                ORDER BY c.flagged_at DESC, c.id DESC
                LIMIT :limit OFFSET :offset
            """),
            {
                **params,
                "limit": per_page,
                "offset": (page - 1) * per_page
            }
        ).mappings().all()

    else:
        filters = """
            WHERE (:email = '' OR LOWER(u.email) = :email)
              AND (
                  :search = ''
                  OR u.name LIKE :pattern
                  OR u.email LIKE :pattern
                  OR b.category LIKE :pattern
              )
        """

        totals = db.session.execute(
            text(f"""
                SELECT
                    COUNT(*) AS total_attempts,
                    COUNT(DISTINCT b.user_id) AS total_users
                FROM blocked_topic_attempts AS b
                LEFT JOIN users AS u ON u.id = b.user_id
                {filters}
            """),
            params
        ).mappings().one()

        total_attempts = int(totals["total_attempts"])
        total_users = int(totals["total_users"])

        total_records = db.session.execute(
            text(f"""
                SELECT COUNT(*)
                FROM (
                    SELECT b.user_id, b.category
                    FROM blocked_topic_attempts AS b
                    LEFT JOIN users AS u ON u.id = b.user_id
                    {filters}
                    GROUP BY b.user_id, b.category
                ) AS grouped_attempts
            """),
            params
        ).scalar() or 0

        total_pages = max(1, math.ceil(total_records / per_page))
        page = min(page, total_pages)

        attempts = db.session.execute(
            text(f"""
                SELECT
                    b.user_id,
                    COALESCE(u.name, 'Unknown User') AS name,
                    u.email,
                    b.category,
                    COUNT(*) AS attempt_count
                FROM blocked_topic_attempts AS b
                LEFT JOIN users AS u ON u.id = b.user_id
                {filters}
                GROUP BY b.user_id, u.name, u.email, b.category
                ORDER BY
                    attempt_count DESC,
                    b.user_id ASC,
                    b.category ASC
                LIMIT :limit OFFSET :offset
            """),
            {
                **params,
                "limit": per_page,
                "offset": (page - 1) * per_page
            }
        ).mappings().all()

    return render_template(
        "admin/content_moderation.html",
        tab=tab,
        search=search,
        selected_email=selected_email,
        cases=cases,
        attempts=attempts,
        total_records=int(total_records),
        total_attempts=total_attempts,
        total_users=total_users,
        page=page,
        total_pages=total_pages
    )
@admin.route("/needs-review", methods=["GET"])
def needs_review():
    if not admin_required():
        return redirect(url_for("auth.login"))

    return redirect(url_for(
        "admin.content_moderation",
        tab="reviews",
        page=request.args.get("page", 1, type=int) or 1
    ))
    
    
@admin.route("/api/needs-review/count", methods=["GET"])
def needs_review_count_api():
    if not admin_required():
        return jsonify({
            "success": False,
            "message": "Please sign in as an administrator."
        }), 401

    try:
        count = db.session.execute(
            text("""
                SELECT COUNT(*)
                FROM moderation_review_cases
                WHERE pending = 1
            """)
        ).scalar() or 0

        response = jsonify({
            "success": True,
            "pending_count": int(count)
        })
        response.headers["Cache-Control"] = "no-store"

        return response

    except Exception:
        db.session.rollback()
        current_app.logger.exception(
            "Unable to load pending moderation review count"
        )

        return jsonify({
            "success": False,
            "message": "Unable to load review count."
        }), 500
def moderation_admin_allowed():
    if not admin_required() or not session.get("user_id"):
        return False

    administrator = db.session.get(User, session["user_id"])

    return (
        administrator is not None
        and (administrator.role or "").strip().lower() == "admin"
        and (administrator.status or "active").strip().lower()
            == "active"
    )


def moderation_date(value):
    return value.isoformat() + "Z" if value else None


# Load a case before showing the review form.
@admin.route(
    "/api/moderation/cases/<int:case_id>",
    methods=["GET"],
)
def moderation_case_details_api(case_id):
    try:
        if not moderation_admin_allowed():
            return jsonify({
                "success": False,
                "message": "Administrator access is required.",
            }), 403

        case = db.session.execute(
            text("""
                SELECT
                    c.id,
                    c.user_id,
                    c.pending,
                    c.restriction_count,
                    c.flagged_at,
                    u.name,
                    u.email,
                    u.status
                FROM moderation_review_cases AS c
                JOIN users AS u ON u.id = c.user_id
                WHERE c.id = :case_id
            """),
            {"case_id": case_id},
        ).mappings().first()

        if case is None:
            return jsonify({
                "success": False,
                "message": "Review case not found.",
            }), 404

        if not case["pending"]:
            return jsonify({
                "success": False,
                "message": "This case has already been reviewed.",
            }), 409

        suspension = db.session.execute(
            text("""
                SELECT
                    id,
                    trigger_restriction_id,
                    reason,
                    started_at,
                    suspended_until
                FROM account_suspension_events
                WHERE user_id = :uid
                ORDER BY id DESC
                LIMIT 1
            """),
            {"uid": case["user_id"]},
        ).mappings().first()

        if (
            suspension is None
            or suspension["started_at"] != case["flagged_at"]
        ):
            return jsonify({
                "success": False,
                "message": (
                    "Matching suspension history was not found. "
                    "Refresh the moderation page."
                ),
            }), 409

        # Earlier suspension events start a new escalation cycle.
        previous_trigger = db.session.execute(
            text("""
                SELECT COALESCE(MAX(trigger_restriction_id), 0)
                FROM account_suspension_events
                WHERE user_id = :uid
                  AND id < :suspension_id
            """),
            {
                "uid": case["user_id"],
                "suspension_id": suspension["id"],
            },
        ).scalar() or 0

        restrictions = db.session.execute(
            text("""
                SELECT
                    id,
                    category,
                    started_at,
                    restricted_until
                FROM generator_restriction_events
                WHERE user_id = :uid
                  AND id > :previous_trigger
                  AND id <= :current_trigger
                  AND started_at >= :since
                ORDER BY id ASC
            """),
            {
                "uid": case["user_id"],
                "previous_trigger": previous_trigger,
                "current_trigger": suspension["trigger_restriction_id"],
                "since": (
                    suspension["started_at"] - timedelta(days=7)
                ),
            },
        ).mappings().all()

        if not session.get("moderation_review_csrf"):
            session["moderation_review_csrf"] = token_urlsafe(32)

        response = jsonify({
            "success": True,
            "csrf_token": session["moderation_review_csrf"],
            "data": {
                "case_id": case["id"],
                "user_id": case["user_id"],
                "name": case["name"] or "User",
                "email": case["email"] or "",
                "account_status": case["status"] or "active",
                "restriction_count": case["restriction_count"],
                "flagged_at": moderation_date(case["flagged_at"]),
                "suspension_id": suspension["id"],
                "reason": suspension["reason"] or "",
                "suspended_until": moderation_date(
                    suspension["suspended_until"]
                ),
                "restrictions": [
                    {
                        "id": item["id"],
                        "category": item["category"],
                        "started_at": moderation_date(
                            item["started_at"]
                        ),
                        "restricted_until": moderation_date(
                            item["restricted_until"]
                        ),
                    }
                    for item in restrictions
                ],
            },
        })

        response.headers["Cache-Control"] = "no-store"
        return response

    except Exception:
        db.session.rollback()
        current_app.logger.exception(
            "Unable to load moderation case"
        )

        return jsonify({
            "success": False,
            "message": "Unable to load this review case.",
        }), 500


# Save the administrator's review.
@admin.route(
    "/api/moderation/cases/<int:case_id>/review",
    methods=["POST"],
)
def moderation_case_review_api(case_id):
    if not admin_required() or not session.get("user_id"):
        return jsonify({
            "success": False,
            "message": "Administrator access is required.",
        }), 403

    stored_token = session.get("moderation_review_csrf")
    submitted_token = request.headers.get(
        "X-Moderation-CSRF",
        "",
    )

    if (
        not isinstance(stored_token, str)
        or not stored_token
        or not compare_digest(stored_token, submitted_token)
    ):
        return jsonify({
            "success": False,
            "message": "Please reopen the review form and try again.",
        }), 403

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "message": "Valid review data is required.",
        }), 400

    try:
        result = review_moderation_case(
            case_id=case_id,
            admin_id=session["user_id"],
            action=data.get("action"),
            reason=data.get("reason"),
            expected_suspension_id=data.get("suspension_id"),
        )

        response = jsonify({
            "success": True,
            "data": result,
            "message": result["message"],
        })
        response.headers["Cache-Control"] = "no-store"

        return response

    except ModerationReviewError as error:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": str(error),
        }), error.status

    except Exception:
        db.session.rollback()
        current_app.logger.exception(
            "Unable to save moderation review"
        )

        return jsonify({
            "success": False,
            "message": "Unable to save this review.",
        }), 500   