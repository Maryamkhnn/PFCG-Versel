from datetime import datetime, timedelta

from sqlalchemy import text

from app.database import db


def add_restriction_notification(user_id, until):
    """Called while the user's database row is locked."""

    local_end = until + timedelta(hours=5)

    message = (
        "Content generation is restricted after repeated blocked "
        "topic attempts. "
        f"Available again on {local_end:%d %b %Y at %I:%M:%S %p} PKT. "
        "SEO and Humanize remain available."
    )

    existing = db.session.execute(
        text("""
            SELECT id
            FROM user_notifications
            WHERE user_id = :uid
              AND notification_type = 'generator_restricted'
              AND message = :message
            LIMIT 1
        """),
        {"uid": user_id, "message": message},
    ).scalar_one_or_none()

    if existing is None:
        db.session.execute(
            text("""
                INSERT INTO user_notifications
                    (
                        user_id,
                        notification_type,
                        title,
                        message,
                        is_read,
                        created_at
                    )
                VALUES
                    (
                        :uid,
                        'generator_restricted',
                        'Content generation restricted',
                        :message,
                        0,
                        :created
                    )
            """),
            {
                "uid": user_id,
                "message": message,
                "created": datetime.utcnow(),
            },
        )


def sync_generator_restriction(user_id):
    """Check expiry and create each restoration notification once."""

    try:
        row = db.session.execute(
            text("""
                SELECT generator_restricted_until
                FROM users
                WHERE id = :uid
                FOR UPDATE
            """),
            {"uid": user_id},
        ).mappings().first()

        if row is None:
            db.session.rollback()
            return None

        until = row["generator_restricted_until"]
        now = datetime.utcnow()

        if until is not None and until > now:
            # Also handles restrictions created before this feature.
            add_restriction_notification(user_id, until)

        elif until is not None:
            db.session.execute(
                text("""
                    UPDATE users
                    SET generator_restricted_until = NULL
                    WHERE id = :uid
                """),
                {"uid": user_id},
            )

            db.session.execute(
                text("""
                    INSERT INTO user_notifications
                        (
                            user_id,
                            notification_type,
                            title,
                            message,
                            is_read,
                            created_at
                        )
                    VALUES
                        (
                            :uid,
                            'generator_restored',
                            'Generator restriction ended',
                            :message,
                            0,
                            :created
                        )
                """),
                {
                    "uid": user_id,
                    "message": (
                        "Your temporary content generation restriction "
                        "has ended."
                    ),
                    "created": now,
                },
            )

            until = None

        db.session.commit()
        return until

    except Exception:
        db.session.rollback()
        raise