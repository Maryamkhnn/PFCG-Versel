from flask import Blueprint, jsonify, session
from sqlalchemy import text

from app.database import db
from datetime import datetime

from app.user.services.generator_restriction_service import (
    sync_generator_restriction,
)

notifications = Blueprint(
    "notifications",
    __name__,
    url_prefix="/user/api/notifications"
)


def unauthorized_response():
    return jsonify({
        "success": False,
        "message": "Please sign in again.",
        "data": [],
        "unread_count": 0
    }), 401


# ============================================================
# GET NOTIFICATIONS
# URL: /user/api/notifications
# ============================================================

@notifications.route("", methods=["GET"])
@notifications.route("/", methods=["GET"])
def get_notifications():

    user_id = session.get("user_id")

    if not user_id:
        return unauthorized_response()

    try:
        restricted_until = sync_generator_restriction(user_id)
        rows = db.session.execute(
            text("""
                SELECT
                    id,
                    notification_type,
                    title,
                    message,
                    is_read,
                    created_at
                FROM user_notifications
                WHERE user_id = :user_id
                ORDER BY created_at DESC, id DESC
                LIMIT 30
            """),
            {
                "user_id": user_id
            }
        ).mappings().all()

        unread_count = db.session.execute(
            text("""
                SELECT COUNT(*)
                FROM user_notifications
                WHERE user_id = :user_id
                  AND is_read = 0
            """),
            {
                "user_id": user_id
            }
        ).scalar() or 0

        data = []

        for row in rows:
            data.append({
                "id": row["id"],
                "notification_type": (
                    row["notification_type"] or "info"
                ),
                "title": row["title"] or "Notification",
                "message": row["message"] or "",
                "is_read": bool(row["is_read"]),
                "created_at": (
                    row["created_at"].isoformat() + "Z"
                    if row["created_at"]
                    else None
                )
            })

            return jsonify({
            "success": True,
            "data": data,
            "unread_count": int(unread_count),
            "server_now": datetime.utcnow().isoformat() + "Z",
            "generator_restricted_until": (
                restricted_until.isoformat() + "Z"
                if restricted_until
                else None
            ),
        })

    except Exception:

        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "Unable to load notifications.",
            "data": [],
            "unread_count": 0
        }), 500


# ============================================================
# MARK ONE AS READ
# URL: /user/api/notifications/<id>/read
# ============================================================

@notifications.route(
    "/<int:notification_id>/read",
    methods=["POST"]
)
def mark_notification_read(notification_id):

    user_id = session.get("user_id")

    if not user_id:
        return unauthorized_response()

    try:
        result = db.session.execute(
            text("""
                UPDATE user_notifications
                SET is_read = 1
                WHERE id = :notification_id
                  AND user_id = :user_id
            """),
            {
                "notification_id": notification_id,
                "user_id": user_id
            }
        )

        if result.rowcount == 0:
            db.session.rollback()

            return jsonify({
                "success": False,
                "message": "Notification not found."
            }), 404

        db.session.commit()

        unread_count = db.session.execute(
            text("""
                SELECT COUNT(*)
                FROM user_notifications
                WHERE user_id = :user_id
                  AND is_read = 0
            """),
            {
                "user_id": user_id
            }
        ).scalar() or 0

        return jsonify({
            "success": True,
            "message": "Notification marked as read.",
            "unread_count": int(unread_count)
        })

    except Exception:

        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "Unable to update notification."
        }), 500


# ============================================================
# MARK ALL AS READ
# URL: /user/api/notifications/read-all
# ============================================================

@notifications.route("/read-all", methods=["POST"])
def mark_all_notifications_read():

    user_id = session.get("user_id")

    if not user_id:
        return unauthorized_response()

    try:
        db.session.execute(
            text("""
                UPDATE user_notifications
                SET is_read = 1
                WHERE user_id = :user_id
                  AND is_read = 0
            """),
            {
                "user_id": user_id
            }
        )

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "All notifications marked as read.",
            "unread_count": 0
        })

    except Exception:

        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "Unable to update notifications."
        }), 500