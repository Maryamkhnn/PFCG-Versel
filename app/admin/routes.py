
from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    session,
    request,
    jsonify
)
from flask import request
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
    moderate_user_account
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
            "phone": user.phone or "",
            "role": user.role or "",
            "status": user.status or "active"
        }
    })

# =====================================================
# EDIT USER
# =====================================================

@admin.route(
    "/users/<int:user_id>/edit",
    methods=["POST"]
)
def edit_user(user_id):

    if not admin_required():

        return jsonify({
            "success": False,
            "message": "Unauthorized access."
        }), 401


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


    if not name or not email:

        return jsonify({
            "success": False,
            "message": "Name and email are required."
        }), 400


    try:

        # ---------------------------------------------
        # GET OLD USER INFORMATION
        # ---------------------------------------------

        old_user = get_user_by_id(
            user_id
        )


        if not old_user:

            return jsonify({
                "success": False,
                "message": "User not found."
            }), 404


        old_email = old_user.email


        # ---------------------------------------------
        # UPDATE USER
        # ---------------------------------------------

        user = update_user(
            user_id,
            data
        )


        if not user:

            return jsonify({
                "success": False,
                "message": "User not found."
            }), 404

        # ---------------------------------------------
        # SAVE ADMIN ACTIVITY
        # ---------------------------------------------

        details = (
            f"{old_email} → {user.email}"
            if old_email != user.email
            else user.email
        )


        add_admin_log(

            admin_id=session.get(
                "user_id"
            ),

            admin_email=session.get(
                "user_email"
            ),

            action="Updated User",

            target_type="User",

            target_details=details

        )


        return jsonify({
            "success": True,
            "message": "User updated successfully."
        })


    except Exception as e:

        db.session.rollback()

        print(
            "UPDATE USER ERROR:",
            e
        )

        return jsonify({
            "success": False,
            "message": "Unable to update user."
        }), 500
# =====================================================
# BLOCK / UNBLOCK USER
# =====================================================

@admin.route(
    "/users/<int:user_id>/toggle-block",
    methods=["POST"]
)
def toggle_block_user(user_id):

    if not admin_required():
        return jsonify({
            "success": False,
            "message": "Unauthorized access."
        }), 401

    user = User.query.filter_by(
        id=user_id,
        role="user"
    ).first()

    if not user:
        return jsonify({
            "success": False,
            "message": "User not found."
        }), 404

    try:

        current_status = (
            user.status or "active"
        ).strip().lower()

        if current_status == "blocked":
            user.status = "active"
            message = "User unblocked successfully."
        else:
            user.status = "blocked"
            message = "User blocked successfully."

        db.session.commit()

        return jsonify({
            "success": True,
            "status": user.status,
            "message": message
        })

    except Exception as e:

        db.session.rollback()

        print(
            "BLOCK USER ERROR:",
            e
        )

        return jsonify({
            "success": False,
            "message": "Unable to update user status."
        }), 500


# =====================================================
# PROFESSIONAL USER MODERATION
# =====================================================

@admin.route("/users/<int:user_id>/moderate", methods=["POST"])
def moderate_user(user_id):

    if not admin_required():
        return jsonify({
            "success": False,
            "message": "Unauthorized access."
        }), 401

    data = request.get_json(silent=True) or {}

    try:
        result = moderate_user_account(
            user_id=user_id,
            admin_id=session.get("user_id"),
            admin_email=session.get("user_email"),
            action=data.get("action"),
            reason=data.get("reason"),
            ip_address=request.headers.get(
                "X-Forwarded-For",
                request.remote_addr
            )
        )

        if not result:
            return jsonify({
                "success": False,
                "message": "User not found."
            }), 404

        return jsonify({
            "success": True,
            "status": result["status"],
            "message": result["title"] + " successfully."
        })

    except ValueError as error:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": str(error)
        }), 400

    except Exception as error:
        db.session.rollback()
        print("MODERATE USER ERROR:", error)
        return jsonify({
            "success": False,
            "message": "Unable to complete moderation action."
        }), 500

# =====================================================
# DELETE USER
# =====================================================

@admin.route(
    "/users/<int:user_id>/delete",
    methods=["POST"]
)
def remove_user(user_id):

    if not admin_required():

        return jsonify({
            "success": False,
            "message": "Unauthorized access."
        }), 401


    try:

        # ---------------------------------------------
        # GET USER BEFORE DELETE
        # ---------------------------------------------

        user = get_user_by_id(
            user_id
        )


        if not user:

            return jsonify({
                "success": False,
                "message": "User not found."
            }), 404

        deletion_state = db.session.execute(
            text("""
                SELECT status, deletion_scheduled_at,
                       deletion_scheduled_at <= NOW() AS deletion_due
                FROM users
                WHERE id = :user_id AND role = 'user'
            """),
            {"user_id": user_id}
        ).mappings().first()

        if (
            not deletion_state
            or deletion_state["status"] != "pending_deletion"
            or not deletion_state["deletion_due"]
        ):
            return jsonify({
                "success": False,
                "message": (
                    "Permanent deletion is allowed only after the "
                    "7-day scheduled-deletion period is complete."
                )
            }), 409


        # Save information BEFORE deletion

        user_email = (
            user.email
            or
            f"User ID: {user_id}"
        )


        # ---------------------------------------------
        # DELETE USER
        # ---------------------------------------------

        deleted = delete_user(
            user_id
        )


        if not deleted:

            return jsonify({
                "success": False,
                "message": "User not found."
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

            action="Deleted User",

            target_type="User",

            target_details=user_email

        )


        return jsonify({
            "success": True,
            "message": "User deleted successfully."
        })


    except Exception as e:

        db.session.rollback()

        print(
            "DELETE USER ERROR:",
            e
        )

        return jsonify({
            "success": False,
            "message": "Unable to delete user."
        }), 500

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
# =====================================================
# UPDATE SETTINGS
# =====================================================

@admin.route(
    "/settings/update",
    methods=["POST"]
)
def update_settings():

    # =================================================
    # ADMIN AUTHENTICATION
    # =================================================

    if not admin_required():

        return jsonify({
            "success": False,
            "message": "Unauthorized access."
        }), 401


    # =================================================
    # GET JSON DATA
    # =================================================

    data = request.get_json(
        silent=True
    ) or {}


    # =================================================
    # SITE NAME
    # =================================================

    site_name = str(
        data.get(
            "site_name",
            ""
        )
    ).strip()

    if not site_name:

        return jsonify({
            "success": False,
            "message": "Site name is required."
        }), 400


    # =================================================
    # CONVERT NUMBER VALUES
    # =================================================

    try:

        plagiarism_threshold = int(
            data.get(
                "plagiarism_threshold",
                20
            )
        )

        seo_target_score = int(
            data.get(
                "seo_target_score",
                70
            )
        )

        default_word_limit = int(
            data.get(
                "default_word_limit",
                500
            )
        )

    except (TypeError, ValueError):

        return jsonify({
            "success": False,
            "message":
                "Settings contain invalid number values."
        }), 400


    # =================================================
    # PLAGIARISM VALIDATION
    # =================================================

    if (
        plagiarism_threshold < 0
        or
        plagiarism_threshold > 100
    ):

        return jsonify({
            "success": False,
            "message":
                "Plagiarism threshold must be between 0 and 100."
        }), 400


    # =================================================
    # SEO VALIDATION
    # =================================================

    if (
        seo_target_score < 0
        or
        seo_target_score > 100
    ):

        return jsonify({
            "success": False,
            "message":
                "SEO target score must be between 0 and 100."
        }), 400


    # =================================================
    # WORD LIMIT VALIDATION
    # =================================================

    if (
        default_word_limit < 100
        or
        default_word_limit > 5000
    ):

        return jsonify({
            "success": False,
            "message":
                "Default word limit must be between 100 and 5000."
        }), 400



    # =================================================
    # FINAL SETTINGS DATA
    # =================================================

    settings_data = {

        "site_name":
            site_name,

        "plagiarism_threshold":
            plagiarism_threshold,

        "seo_target_score":
            seo_target_score,

        "default_word_limit":
            default_word_limit,

    }


    # =================================================
    # SAVE SETTINGS
    # =================================================

    try:

        update_admin_settings(
            settings_data
        )


        # =================================================
        # ACTIVITY LOG
        # =================================================

        add_admin_log(

            admin_id=session.get(
                "user_id"
            ),

            admin_email=session.get(
                "user_email"
            ),

            action="Updated Settings",

            target_type="System Settings",

            target_details=(
                "Administrator updated "
                "system settings."
            )
        )


        # =================================================
        # SUCCESS RESPONSE
        # =================================================

        return jsonify({
            "success": True,
            "message":
                "Settings saved successfully."
        })


    except Exception as e:

        db.session.rollback()

        print(
            "UPDATE SETTINGS ERROR:",
            e
        )

        return jsonify({
            "success": False,
            "message":
                "Unable to save settings."
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
    if session.get("role") != "admin":
        return redirect(url_for("auth.login"))

    selected_email = request.args.get("email", "").strip().lower()
    search = request.args.get("search", "").strip()

    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1

    per_page = 5

    filters = """
        WHERE (:selected_email = '' OR LOWER(u.email) = :selected_email)
          AND (
              :search = ''
              OR u.name LIKE :search_pattern
              OR u.email LIKE :search_pattern
              OR b.category LIKE :search_pattern
          )
    """

    params = {
        "selected_email": selected_email,
        "search": search,
        "search_pattern": f"%{search}%"
    }

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
    ).scalar_one()

    total_pages = max(1, math.ceil(total_records / per_page))
    page = min(page, total_pages)

    attempts = db.session.execute(
        text(f"""
            SELECT
                b.user_id,
                COALESCE(u.name, 'Unknown user') AS name,
                COALESCE(u.email, 'No email') AS email,
                b.category,
                COUNT(*) AS attempt_count
            FROM blocked_topic_attempts AS b
            LEFT JOIN users AS u ON u.id = b.user_id
            {filters}
            GROUP BY b.user_id, u.name, u.email, b.category
            ORDER BY attempt_count DESC, email ASC, b.user_id ASC, b.category ASC
            LIMIT :limit OFFSET :offset
        """),
        {
            **params,
            "limit": per_page,
            "offset": (page - 1) * per_page
        }
    ).mappings().all()

    return render_template(
        "admin/blocked_attempts.html",
        attempts=attempts,
        selected_email=selected_email,
        search=search,
        page=page,
        total_pages=total_pages,
        total_records=total_records,
        total_attempts=totals["total_attempts"],
        total_users=totals["total_users"],
        per_page=per_page
    )
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

