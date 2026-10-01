from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.database import db
from app.models import User


class AccountError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def require_user(user_email):
    user = User.query.filter_by(email=user_email).first()

    if user is None:
        raise AccountError("User account not found.", 404)

    return user


def serialize_user(user):
    return {
        "id": user.id,
        "name": user.name or "",
        "username": user.username or "",
        "email": user.email or "",
        "role": user.role or "user",
        "profile_picture": user.profile_picture or ""
    }


def get_account(user_email):
    return serialize_user(require_user(user_email))


def update_account(user_email, data):
    name = data.get("name")
    username = data.get("username")

    if not isinstance(name, str) or not name.strip():
        raise AccountError("Full name is required.")

    if not isinstance(username, str) or len(username.strip()) < 3:
        raise AccountError(
            "Username must contain at least 3 characters."
        )

    name = name.strip()
    username = username.strip()

    # Respect actual model column limits when available.
    for field, value in (("name", name), ("username", username)):
        column = User.__table__.columns.get(field)
        limit = getattr(column.type, "length", None) if column is not None else None

        if limit and len(value) > limit:
            raise AccountError(
                f"{field.title()} must not exceed {limit} characters."
            )

    user = require_user(user_email)

    existing = User.query.filter(
        User.username == username,
        User.id != user.id
    ).first()

    if existing:
        raise AccountError("Username is already taken.", 409)

    user.name = name
    user.username = username

    try:
        # Preserve support for the old settings profile API.
        # If phone is omitted, the stored phone remains unchanged.
        if "phone" in data:
            phone = data["phone"]

            if phone is not None and not isinstance(phone, str):
                raise AccountError("Phone must be text.")

            phone = (phone or "").strip() or None

            db.session.execute(
                text("""
                    UPDATE users
                    SET phone = :phone
                    WHERE id = :user_id
                """),
                {
                    "phone": phone,
                    "user_id": user.id
                }
            )

        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        raise AccountError(
            "These account details could not be saved. "
            "The username may already be taken.",
            409
        )

    return serialize_user(user)


def change_account_password(user_email, data):
    current = data.get("current_password")
    new = data.get("new_password")
    confirmation = data.get("confirm_password")

    if not isinstance(current, str) or not current:
        raise AccountError("Please enter your current password.")

    if not isinstance(new, str) or len(new) < 8:
        raise AccountError(
            "New password must contain at least 8 characters."
        )

    if not isinstance(confirmation, str) or new != confirmation:
        raise AccountError("New passwords do not match.")

    if current == new:
        raise AccountError(
            "New password must be different from your current password."
        )

    user = require_user(user_email)

    if not user.check_password(current):
        raise AccountError("Current password is incorrect.")

    user.set_password(new)
    db.session.commit()


def update_account_picture(user_email, picture_path):
    user = require_user(user_email)
    user.profile_picture = picture_path

    db.session.commit()

    return {"profile_picture": picture_path}


# Keep existing preferences APIs functional.
# These are not displayed as unused switches in My Account.

def get_account_settings(user_email):
    profile = get_account(user_email)

    row = db.session.execute(
        text("""
            SELECT
                phone,
                default_content_type,
                default_word_count,
                email_notifications,
                system_notifications
            FROM users
            WHERE id = :user_id
        """),
        {"user_id": profile["id"]}
    ).mappings().first()

    if row:
        profile.update({
            "phone": row["phone"] or "",
            "default_content_type": row["default_content_type"] or "Blog",
            "default_word_count": row["default_word_count"] or 500,
            "email_notifications": bool(row["email_notifications"]),
            "system_notifications": bool(row["system_notifications"])
        })

    return profile


def update_account_preferences(user_email, data):
    content_type = data.get("default_content_type")
    word_count = data.get("default_word_count")

    allowed_types = {
        "Blog", "Essay", "Article", "Assignment", "Report"
    }

    if not isinstance(content_type, str) or content_type not in allowed_types:
        raise AccountError("Invalid content type.")

    if (
        isinstance(word_count, bool)
        or not isinstance(word_count, (int, str))
    ):
        raise AccountError("Invalid word count.")

    try:
        word_count = int(word_count)
    except (ValueError, TypeError):
        raise AccountError("Invalid word count.")

    if word_count not in {300, 500, 1000, 1500}:
        raise AccountError("Invalid word count.")

    user = require_user(user_email)

    # Preserve flags when an older client does not send them.
    current = get_account_settings(user_email)

    email_notifications = data.get(
        "email_notifications",
        current["email_notifications"]
    )

    system_notifications = data.get(
        "system_notifications",
        current["system_notifications"]
    )

    if (
        not isinstance(email_notifications, bool)
        or not isinstance(system_notifications, bool)
    ):
        raise AccountError("Notification preferences must be true or false.")

    db.session.execute(
        text("""
            UPDATE users
            SET
                default_content_type = :content_type,
                default_word_count = :word_count,
                email_notifications = :email_notifications,
                system_notifications = :system_notifications
            WHERE id = :user_id
        """),
        {
            "content_type": content_type,
            "word_count": word_count,
            "email_notifications": email_notifications,
            "system_notifications": system_notifications,
            "user_id": user.id
        }
    )

    db.session.commit()