from datetime import datetime

from sqlalchemy import text

from app.database import db

from app.user.services.automatic_moderation_service import (
    _add_notification,
    _send_moderation_email,
)


def sync_generator_restriction(user_id):
    """
    Clear an expired generator restriction.

    Save the restoration notification in the same transaction.
    Send the email after committing and releasing the user lock.
    """

    email_details = None

    try:
        user = db.session.execute(
            text("""
                SELECT
                    id,
                    name,
                    email,
                    status,
                    generator_restricted_until
                FROM users
                WHERE id = :uid
                FOR UPDATE
            """),
            {"uid": user_id},
        ).mappings().first()

        if user is None:
            db.session.rollback()
            return None

        until = user["generator_restricted_until"]
        now = datetime.utcnow()

        # No restriction, or its timer is still running.
        if until is None or until > now:
            db.session.commit()
            return until

        # The locked row ensures concurrent requests cannot
        # create multiple restoration notifications.
        db.session.execute(
            text("""
                UPDATE users
                SET generator_restricted_until = NULL
                WHERE id = :uid
            """),
            {"uid": user_id},
        )

        account_status = (
            user["status"] or "active"
        ).strip().lower()

        title = "Generation restriction ended"

        if account_status == "active":
            message = (
                "Your temporary content generation and humanization "
                "restriction has ended. "
                "Generate, Regenerate and Humanize are available again. "
                "Please follow the content guidelines."
            )
        else:
            message = (
                "Your temporary content generation and humanization "
                "restriction has ended. "
                "A separate account restriction is still in effect. "
                "Please check the account-status message for details."
            )

        _add_notification(
            user["id"],
            "generator_restored",
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

        # Clear the timer and save the notification together.
        db.session.commit()

    except Exception:
        db.session.rollback()
        raise

    # Email sending does not hold the database lock.
    if email_details is not None:
        _send_moderation_email(*email_details)

    return None