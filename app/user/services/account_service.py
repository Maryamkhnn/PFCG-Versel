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

def update_account_picture(user_email, picture_path, picture_bytes):
    user = require_user(user_email)

    db.session.execute(
        text("""
            UPDATE users
            SET
                profile_picture = :picture_path,
                profile_picture_data = :picture_bytes
            WHERE id = :user_id
        """),
        {
            "picture_path": picture_path,
            "picture_bytes": picture_bytes,
            "user_id": user.id
        }
    )

    db.session.commit()
    db.session.refresh(user)

    return {
        "profile_picture": user.profile_picture
    }

