from flask import Blueprint, jsonify, session, current_app
from sqlalchemy import text

from app.database import db
from app.user.decorators import login_required
from flask import Blueprint, jsonify, session, current_app, request
# Dashboard
from app.user.controllers.dashboard_controller import (
    dashboard_page
)
from app.user.services.streaming_generation_service import (
    _validate_topic_intent,
    InvalidTopicError,
    BlockedTopicError,
)
# Generator
from app.user.controllers.generator_controller import (
    generator_page,
    generate_content,
    humanize_content
)

# Plagiarism
from app.user.controllers.plagiarism_controller import (
    plagiarism_content
)

# Content
from app.user.controllers.content_controller import (
    edit_content_page,
    my_content_page,
    my_content_api,
    saved_documents_page,
    save_document_api,
    delete_document_api
)

# Editor
from app.user.controllers.edit_controller import (
    get_edit_content_api,
    get_edit_content_by_id_api,
    update_edit_content_api,
    editor_history_api,
    editor_version_api,
    editor_export_api,
    editor_assist_api
)

# Saved documents
from app.user.controllers.saved_controller import (
    get_saved_documents_api
)

# Reports
from app.user.controllers.report_controller import (
    reports_page,
    get_reports_api,
    get_single_report_api,
    delete_report_api
)

# Feedback
from app.user.controllers.feedback_controller import (
    feedback_page,
    submit_feedback_api,
    get_feedback_api,
    get_latest_feedback_api
)

# Profile
from app.user.controllers.account_controller import (
    account_page,
    legacy_account_page,
    get_account_api,
    update_account_api,
    upload_account_picture_api,
    change_account_password_api,
    get_account_settings_api,
    save_account_preferences_api,
)


# SEO
from app.user.controllers.seo_controller import (
    seo_analysis_page,
    seo_get_content_api,
    seo_analyze_api,
    seo_history_api
)

from app.user.controllers.account_controller import (
    account_page,
    legacy_account_page,
    get_account_api,
    update_account_api,
    upload_account_picture_api,
    change_account_password_api,
    get_account_settings_api,
    save_account_preferences_api
)
# ============================================================
# BLUEPRINT
# ============================================================

user = Blueprint(
    "user",
    __name__,
    url_prefix="/user"
)
@user.route("/api/prompt-suggestions", methods=["POST"])
@login_required
def prompt_suggestions():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(success=False, suggestions=[]), 400

    topic = data.get("prompt")

    if not isinstance(topic, str):
        return jsonify(success=False, suggestions=[]), 400

    topic = topic.strip()

    if len(topic) < 4:
        return jsonify(success=True, suggestions=[])

    if len(topic) > 3000:
        return jsonify(success=False, suggestions=[]), 400

    try:
        suggestions = _validate_topic_intent(topic)

        return jsonify(
            success=True,
            suggestions=suggestions,
        )

    except InvalidTopicError as error:
        return jsonify(
            success=True,
            suggestions=error.suggestions,
        )

    except BlockedTopicError:
        # Preview does not record a blocked attempt.
        return jsonify(
            success=True,
            suggestions=[],
        )

    except RuntimeError:
        current_app.logger.exception(
            "Live prompt suggestions failed"
        )
        return jsonify(
            success=False,
            suggestions=[],
        ), 503
# DASHBOARD

@user.route("/dashboard")
# decorator
@login_required 
def dashboard():
    return dashboard_page()

# GENERATOR

@user.route("/generator")
@login_required
def generator():
    return generator_page()

@user.route("/generate", methods=["POST"])
@login_required
def generate():
    return generate_content()


@user.route("/humanize", methods=["POST"])
@login_required
def humanize():
    return humanize_content()

@user.route("/plagiarism", methods=["POST"])
@login_required
def plagiarism():
    return plagiarism_content()

# ============================================================
# MY CONTENT
# ============================================================

@user.route("/my-content")
@login_required
def my_content():
    return my_content_page()


@user.route("/api/my-content", methods=["GET", "POST"])
@login_required
def api_my_content():
    return my_content_api()


@user.route("/save-document", methods=["POST"])
@login_required
def save_document():
    return save_document_api()


@user.route(
    "/api/delete-document/<int:document_id>",
    methods=["POST"]
)
@login_required
def delete_document(document_id):
    return delete_document_api(document_id)


# ============================================================
# EDITOR PAGE
# ============================================================

@user.route("/edit-content")
@login_required
def edit_content():
    return edit_content_page()


# ============================================================
# EDITOR APIs
# ============================================================

@user.route("/api/edit-content", methods=["GET"])
@login_required
def api_edit_content():
    return get_edit_content_api()


@user.route("/api/edit-content/get", methods=["POST"])
@login_required
def api_get_edit_content():
    return get_edit_content_by_id_api()


@user.route("/api/edit-content/update", methods=["POST"])
@login_required
def api_update_edit_content():
    return update_edit_content_api()


@user.route("/api/edit-content/history", methods=["POST"])
@login_required
def api_editor_history():
    return editor_history_api()


@user.route("/api/edit-content/version", methods=["POST"])
@login_required
def api_editor_version():
    return editor_version_api()


@user.route("/api/edit-content/export", methods=["POST"])
@login_required
def api_editor_export():
    return editor_export_api()


@user.route("/api/edit-content/assist", methods=["POST"])
@login_required
def api_editor_assist():
    return editor_assist_api()


# ============================================================
# SAVED DOCUMENTS PAGE AND LIST
# ============================================================

@user.route("/saved-documents")
@login_required
def saved_documents():
    return saved_documents_page()


@user.route("/api/saved-documents", methods=["GET"])
@login_required
def api_saved_documents():
    return get_saved_documents_api()


# ============================================================
# REMOVE SAVED DOCUMENT
#
# Both URLs intentionally use the same implementation.
# The older URL is retained for existing frontend references.
# ============================================================

@user.route(
    "/api/saved-documents/<int:document_id>/remove",
    methods=["POST"],
    endpoint="remove_saved_document_only"
)
@user.route(
    "/api/delete-saved-document/<int:document_id>",
    methods=["POST"]
)
@login_required
def api_delete_saved_document(document_id):

    user_id = session.get("user_id")

    if not user_id:
        return jsonify({
            "success": False,
            "message": "Please sign in again."
        }), 401

    try:
        result = db.session.execute(
            text("""
                DELETE FROM saved_documents
                WHERE id = :document_id
                  AND user_id = :user_id
            """),
            {
                "document_id": document_id,
                "user_id": user_id
            }
        )

        removed = result.rowcount > 0

        saved_count = db.session.execute(
            text("""
                SELECT COUNT(*)
                FROM saved_documents
                WHERE user_id = :user_id
            """),
            {
                "user_id": user_id
            }
        ).scalar_one()

        db.session.commit()

        # Treat an already-removed record as an absent saved copy.
        # This also lets a stale browser card disappear safely.
        return jsonify({
            "success": True,
            "message": (
                "Document removed from your saved library."
                if removed
                else "This document is no longer in your saved library."
            ),
            "removed_id": document_id,
            "saved_count": int(saved_count)
        })

    except Exception:
        db.session.rollback()

        current_app.logger.exception(
            "Saved document removal failed"
        )

        return jsonify({
            "success": False,
            "message": (
                "Unable to remove the document. Please try again."
            )
        }), 500


# ============================================================
# SEO
# ============================================================

@user.route("/seo-analysis")
@login_required
def seo_analysis():
    return seo_analysis_page()


@user.route("/api/get-content", methods=["POST"])
@login_required
def api_get_content():
    return seo_get_content_api()


@user.route("/api/analyze-seo", methods=["POST"])
@login_required
def analyze_seo():
    return seo_analyze_api()


@user.route("/api/seo-history", methods=["GET", "POST"])
@login_required
def seo_history():
    return seo_history_api()


# ============================================================
# REPORTS
# ============================================================

@user.route("/reports")
@login_required
def reports():
    return reports_page()


@user.route("/reports/api", methods=["GET"])
@login_required
def reports_api():
    return get_reports_api()


@user.route("/reports/<int:report_id>", methods=["GET"])
@login_required
def single_report_api(report_id):
    return get_single_report_api(report_id)


@user.route(
    "/reports/<int:report_id>/delete",
    methods=["DELETE"]
)
@login_required
def delete_report_api_route(report_id):
    return delete_report_api(report_id)


# ============================================================
# FEEDBACK
# ============================================================

@user.route("/feedback")
@login_required
def feedback():
    return feedback_page()


# Same URL, different HTTP methods and responsibilities.
@user.route("/api/feedback", methods=["POST"])
@login_required
def api_submit_feedback():
    return submit_feedback_api()


@user.route("/api/feedback", methods=["GET"])
@login_required
def api_get_feedback():
    return get_feedback_api()


@user.route("/api/feedback/latest", methods=["GET"])
@login_required
def api_get_latest_feedback():
    return get_latest_feedback_api()

# ============================================================
# MY ACCOUNT
# ============================================================

@user.route("/account")
@login_required
def account():
    return account_page()


# Old page links continue to work.

@user.route("/profile")
@login_required
def profile():
    return legacy_account_page()


@user.route("/settings")
@login_required
def settings():
    return legacy_account_page()


# Account/profile details

@user.route("/api/account", methods=["GET"], endpoint="api_account")
@user.route("/api/profile", methods=["GET"])
@login_required
def api_profile():
    return get_account_api()


# Name / username update

@user.route(
    "/api/account/update",
    methods=["POST"],
    endpoint="api_update_account"
)
@user.route("/api/profile/update", methods=["POST"])
@login_required
def api_update_profile():
    return update_account_api()


# Photo upload

@user.route(
    "/api/account/picture",
    methods=["POST"],
    endpoint="api_account_picture"
)
@user.route("/api/profile/picture", methods=["POST"])
@login_required
def api_upload_profile_picture():
    return upload_account_picture_api()


# Password change

@user.route(
    "/api/account/password",
    methods=["POST"],
    endpoint="api_account_password"
)
@user.route("/api/settings/password", methods=["POST"])
@login_required
def api_change_password():
    return change_account_password_api()


# Compatibility for existing settings clients

@user.route("/api/settings", methods=["GET"])
@login_required
def api_settings():
    return get_account_settings_api()


@user.route("/api/settings/profile", methods=["POST"])
@login_required
def api_settings_update_profile():
    return update_account_api()


@user.route("/api/settings/preferences", methods=["POST"])
@login_required
def api_save_preferences():
    return save_account_preferences_api()
@user.context_processor
def account_header_context():
    from flask import request, url_for
    from app.user.services.account_service import get_account

    if request.endpoint != "user.dashboard":
        return {"account_header_photo": ""}

    user_email = session.get("user_email")

    if not user_email:
        return {"account_header_photo": ""}

    try:
        account_data = get_account(user_email)
        picture = account_data.get("profile_picture") or ""

        # Only use the application's stored profile picture paths.
        if (
            not picture.startswith("uploads/profile_pictures/")
            or ".." in picture.split("/")
            or "\\" in picture
        ):
            picture = ""

        return {
            "account_header_photo": (
                url_for("static", filename=picture)
                if picture else ""
            )
        }

    except Exception:
        db.session.rollback()
        current_app.logger.exception(
            "Unable to load dashboard profile photo"
        )

        return {"account_header_photo": ""}
@user.route(
    "/api/humanized-content/<int:content_id>/edit",
    methods=["POST"]
)
@login_required
def update_humanized_content(content_id):
    from flask import request
    from sqlalchemy import text
    from app.database import db

    user_id = session.get("user_id")
    if not user_id:
        return jsonify({
            "success": False,
            "message": "Please sign in again."
        }), 401

    data = request.get_json(silent=True) or {}
    content = str(data.get("content") or "").strip()

    if not content:
        return jsonify({
            "success": False,
            "message": "Content cannot be empty."
        }), 400

    try:
        result = db.session.execute(
            text("""
                UPDATE humanized_history
                SET humanized_content = :content,
                    word_count = :word_count
                WHERE id = :content_id
                  AND user_id = :user_id
            """),
            {
                "content": content,
                "word_count": len(content.split()),
                "content_id": content_id,
                "user_id": user_id
            }
        )

        if result.rowcount == 0:
            db.session.rollback()
            return jsonify({
                "success": False,
                "message": "Humanized content not found."
            }), 404

        db.session.commit()
        return jsonify({"success": True, "message": "Changes saved."})

    except Exception:
        db.session.rollback()
        current_app.logger.exception("HUMANIZED EDIT ERROR")
        return jsonify({
            "success": False,
            "message": "Unable to save humanized content."
        }), 500