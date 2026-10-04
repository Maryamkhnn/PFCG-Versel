from datetime import datetime

from sqlalchemy import text

from app.database import db

from app.user.services.automatic_moderation_service import (
    _add_notification,
    _send_moderation_email,
)


def sync_account_suspension(user_id):
    """Restore an expired suspension once, under a user-row lock."""

    email_details = None

    try:
        user = db.session.execute(
            text("""
                SELECT
                    id,
                    name,
                    email,
                    status,
                    suspended_until,
                    generator_restricted_until
                FROM users
                WHERE id = :uid
                FOR UPDATE
            """),
            {"uid": user_id},
        ).mappings().first()

        if user is None:
            db.session.rollback()
            return False

        now = datetime.utcnow()
        status = (user["status"] or "active").strip().lower()
        until = user["suspended_until"]

        if (
            status != "suspended"
            or until is None
            or until > now
        ):
            db.session.commit()
            return False

        # Preserve any separate generator restriction.
        db.session.execute(
            text("""
                UPDATE users
                SET status = 'active',
                    suspended_until = NULL,
                    status_reason = NULL,
                    status_changed_at = :changed
                WHERE id = :uid
            """),
            {"uid": user_id, "changed": now},
        )

        title = "Account suspension ended"

        message = (
            "Your temporary PFCG AI account suspension has ended. "
            "You can sign in and access your account again."
        )

        generator_until = user["generator_restricted_until"]

        if generator_until is not None and generator_until > now:
            message += (
                " A separate generation and humanization restriction "
                "is still active until its own expiry."
            )
        else:
            message += (
                " Generate, Regenerate and Humanize are available again."
            )

        message += (
            " Any pending administrator review remains open. "
            "Please follow the content guidelines."
        )

        _add_notification(
            user["id"],
            "account_restored",
            title,
            message,
            now,
        )

        email_details = (
            user["email"],
            user["name"],
            title,
            message,
        )

        db.session.commit()

    except Exception:
        db.session.rollback()
        raise

    # Send after committing and releasing the row lock.
    _send_moderation_email(*email_details)

    return True