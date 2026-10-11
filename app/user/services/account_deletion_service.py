from datetime import datetime, timedelta
from hashlib import sha256
from secrets import compare_digest, randbelow, token_urlsafe
from pathlib import Path

from werkzeug.security import check_password_hash

from flask import current_app
from flask_mail import Message
from sqlalchemy import text
from werkzeug.security import generate_password_hash

from app.database import db
from app.models import User
from app.user.services.account_service import AccountError


OTP_VALID_MINUTES = 10
RESEND_WAIT_SECONDS = 60

REQUEST_WINDOW_MINUTES = 15
MAX_REQUESTS_PER_WINDOW = 10


def request_account_deletion_code(user_id, current_password):
    if (
        not isinstance(current_password, str)
        or not current_password
        or len(current_password) > 1024
    ):
        raise AccountError("Please enter your current password.")

    now = datetime.utcnow()

    try:
        # Lock this account so simultaneous requests are serialized.
        user = (
            User.query
            .filter_by(id=user_id)
            .populate_existing()
            .with_for_update()
            .first()
        )

        if user is None:
            raise AccountError("Account not found.", 404)

        if (user.role or "user").strip().lower() == "admin":
            raise AccountError(
                "Administrator accounts cannot be deleted here.",
                403,
            )

        if (user.status or "active").strip().lower() != "active":
            raise AccountError(
                "Your account is currently unavailable.",
                403,
            )

        rate = db.session.execute(
            text("""
                SELECT window_started_at, request_count
                FROM account_deletion_rate_limits
                WHERE user_id = :uid
                FOR UPDATE
            """),
            {"uid": user.id},
        ).mappings().first()

        window_expired = (
            rate is None
            or rate["window_started_at"]
            + timedelta(minutes=REQUEST_WINDOW_MINUTES)
            <= now
        )

        if window_expired:
            db.session.execute(
                text("""
                    INSERT INTO account_deletion_rate_limits
                        (user_id, window_started_at, request_count)
                    VALUES
                        (:uid, :now, 1)
                    ON DUPLICATE KEY UPDATE
                        window_started_at = :now,
                        request_count = 1
                """),
                {"uid": user.id, "now": now},
            )

        elif rate["request_count"] >= MAX_REQUESTS_PER_WINDOW:
            raise AccountError(
                "Too many deletion requests. "
                "Please try again after 15 minutes.",
                429,
            )

        else:
            db.session.execute(
                text("""
                    UPDATE account_deletion_rate_limits
                    SET request_count = request_count + 1
                    WHERE user_id = :uid
                """),
                {"uid": user.id},
            )

        if not user.check_password(current_password):
            # Keep the failed request count even though access is denied.
            db.session.commit()

            raise AccountError(
                "Current password is incorrect.",
                400,
            )

        previous = db.session.execute(
            text("""
                SELECT last_sent_at
                FROM account_deletion_requests
                WHERE user_id = :uid
                FOR UPDATE
            """),
            {"uid": user.id},
        ).mappings().first()

        if (
            previous is not None
            and previous["last_sent_at"]
            + timedelta(seconds=RESEND_WAIT_SECONDS)
            > now
        ):
            db.session.commit()

            raise AccountError(
                "Please wait 60 seconds before requesting another code.",
                429,
            )

        if not user.email:
            raise AccountError(
                "A valid account email is required.",
                400,
            )

        sender = (
            current_app.config.get("MAIL_DEFAULT_SENDER")
            or current_app.config.get("MAIL_USERNAME")
        )

        if not sender:
            raise AccountError(
                "Email service is unavailable. Please try again later.",
                503,
            )

        code = f"{randbelow(1_000_000):06d}"
        challenge = token_urlsafe(32)

        challenge_hash = sha256(
            challenge.encode("utf-8")
        ).hexdigest()

        expires_at = now + timedelta(
            minutes=OTP_VALID_MINUTES
        )

        db.session.execute(
            text("""
                INSERT INTO account_deletion_requests (
                    user_id,
                    code_hash,
                    challenge_hash,
                    password_snapshot,
                    expires_at,
                    last_sent_at,
                    created_at,
                    failed_attempts
                )
                VALUES (
                    :uid,
                    :code_hash,
                    :challenge_hash,
                    :password_snapshot,
                    :expires_at,
                    :now,
                    :now,
                    0
                )
                ON DUPLICATE KEY UPDATE
                    code_hash = :code_hash,
                    challenge_hash = :challenge_hash,
                    password_snapshot = :password_snapshot,
                    expires_at = :expires_at,
                    last_sent_at = :now,
                    created_at = :now,
                    failed_attempts = 0
            """),
            {
                "uid": user.id,
                "code_hash": generate_password_hash(code),
                "challenge_hash": challenge_hash,
                "password_snapshot": user.password,
                "expires_at": expires_at,
                "now": now,
            },
        )

        recipient = user.email
        name = user.name or "User"
        account_id = user.id

        db.session.commit()

    except Exception:
        db.session.rollback()
        raise

    # Send after releasing the database lock.
    try:
        from app import mail

        message = Message(
            subject="Confirm account deletion | PFCG AI",
            sender=sender,
            recipients=[recipient],
        )

        message.body = (
            f"Hello {name},\n\n"
            "We received a request to permanently delete "
            "your PFCG AI account.\n\n"
            f"Your confirmation code is: {code}\n\n"
            f"This code expires in {OTP_VALID_MINUTES} minutes.\n\n"
            "Confirming deletion will permanently remove your "
            "account, profile photo, generated and saved content, "
            "and associated reports.\n\n"
            "Do not share this code with anyone.\n"
            "If you did not request deletion, do not enter the code. "
            "Your account has not been deleted.\n\n"
            "PFCG AI"
        )

        mail.send(message)

    except Exception:
        current_app.logger.exception(
            "Unable to send account deletion email"
        )

        try:
            # Remove only this request, preserving a newer request.
            db.session.execute(
                text("""
                    DELETE FROM account_deletion_requests
                    WHERE user_id = :uid
                      AND challenge_hash = :challenge_hash
                """),
                {
                    "uid": account_id,
                    "challenge_hash": challenge_hash,
                },
            )

            db.session.commit()

        except Exception:
            db.session.rollback()

            current_app.logger.exception(
                "Unable to invalidate unsent deletion code"
            )

        raise AccountError(
            "Unable to send the confirmation email. "
            "Please try again later.",
            503,
        )

    return {
        "challenge": challenge,
        "expires_at": expires_at.isoformat() + "Z",
        "resend_after_seconds": RESEND_WAIT_SECONDS,
    }
def _remove_old_profile_file(picture_path):
    """Remove only a legacy photo inside the profile upload directory."""

    if not isinstance(picture_path, str):
        return

    relative = picture_path.removeprefix("/static/")
    relative = relative.removeprefix("static/")

    if not relative.startswith("uploads/profile_pictures/"):
        return

    if not current_app.static_folder:
        return

    try:
        folder = (
            Path(current_app.static_folder)
            / "uploads"
            / "profile_pictures"
        ).resolve()

        target = (
            Path(current_app.static_folder) / relative
        ).resolve()

        if target.is_relative_to(folder) and target.is_file():
            target.unlink()

    except Exception:
        current_app.logger.exception(
            "Unable to remove deleted account's legacy profile photo"
        )


def confirm_account_deletion(user_id, challenge, code, confirmation):
    if confirmation != "DELETE":
        raise AccountError(
            "Type DELETE to confirm permanent account deletion."
        )

    if (
        not isinstance(challenge, str)
        or not challenge
        or len(challenge) > 200
    ):
        raise AccountError(
            "Please request a new confirmation code.",
            403,
        )

    if (
        not isinstance(code, str)
        or len(code) != 6
        or any(character not in "0123456789" for character in code)
    ):
        raise AccountError(
            "Enter the 6-digit confirmation code."
        )

    now = datetime.utcnow()

    try:
        user = (
            User.query
            .filter_by(id=user_id)
            .populate_existing()
            .with_for_update()
            .first()
        )

        if user is None:
            raise AccountError("Account not found.", 404)

        if (user.role or "user").strip().lower() == "admin":
            raise AccountError(
                "Administrator accounts cannot be deleted here.",
                403,
            )

        if (user.status or "active").strip().lower() != "active":
            raise AccountError(
                "Your account is currently unavailable.",
                403,
            )

        deletion = db.session.execute(
            text("""
                SELECT
                    code_hash,
                    challenge_hash,
                    password_snapshot,
                    expires_at,
                    failed_attempts
                FROM account_deletion_requests
                WHERE user_id = :uid
                FOR UPDATE
            """),
            {"uid": user.id},
        ).mappings().first()

        if deletion is None:
            raise AccountError(
                "Please request a new confirmation code.",
                400,
            )

        supplied_hash = sha256(
            challenge.encode("utf-8")
        ).hexdigest()

        if not compare_digest(
            deletion["challenge_hash"],
            supplied_hash,
        ):
            raise AccountError(
                "This deletion request is no longer valid. "
                "Please request a new code.",
                403,
            )

        if deletion["expires_at"] <= now:
            raise AccountError(
                "Your confirmation code has expired. "
                "Please request a new code."
            )

        if deletion["failed_attempts"] >= 5:
            raise AccountError(
                "Too many incorrect codes. Please request a new code.",
                429,
            )

        if not compare_digest(
            deletion["password_snapshot"],
            user.password or "",
        ):
            raise AccountError(
                "Your password has changed. "
                "Please start the deletion request again.",
                403,
            )

        if not check_password_hash(deletion["code_hash"], code):
            attempts = int(deletion["failed_attempts"]) + 1

            db.session.execute(
                text("""
                    UPDATE account_deletion_requests
                    SET failed_attempts = :attempts
                    WHERE user_id = :uid
                """),
                {"uid": user.id, "attempts": attempts},
            )

            # Save the failed attempt before returning an error.
            db.session.commit()

            if attempts >= 5:
                raise AccountError(
                    "Too many incorrect codes. "
                    "Please request a new code.",
                    429,
                )

            raise AccountError(
                f"Incorrect code. {5 - attempts} attempt(s) remaining."
            )

        # Historical administrator references must not cause us
        # to delete another user's warning records.
        administrative_reference = db.session.execute(
            text("""
                SELECT id
                FROM user_warnings
                WHERE admin_id = :uid
                LIMIT 1
            """),
            {"uid": user.id},
        ).first()

        if administrative_reference is not None:
            raise AccountError(
                "This account has historical administrator records. "
                "Please contact support to complete deletion.",
                409,
            )

        email = user.email
        name = user.name or "User"
        picture_path = user.profile_picture

        parameters = {
            "uid": user.id,
            "email": email,
        }

        # Generated content owned by this account, including
        # older records where only the email remains.
        owned_content = """
            SELECT id
            FROM generated_content
            WHERE user_id = :uid
               OR (user_id IS NULL AND user_email = :email)
        """

        # Remove content-dependent records before their parent.
        db.session.execute(
            text(f"""
                DELETE FROM editor_versions
                WHERE user_email = :email
                   OR content_id IN ({owned_content})
            """),
            parameters,
        )

        db.session.execute(
            text(f"""
                DELETE FROM seo_history
                WHERE user_email = :email
                   OR (
                       LOWER(TRIM(source_type)) = 'ai'
                       AND source_id IN ({owned_content})
                   )
                   OR (
                       LOWER(TRIM(source_type)) = 'humanized'
                       AND source_id IN (
                           SELECT id
                           FROM humanized_history
                           WHERE user_id = :user_id
                       )
                   )
            """),
            {
                **parameters,
                "user_id": user_id,
            },
        )

        # Explicit cleanup is necessary because these foreign
        # keys use SET NULL rather than CASCADE.
        # Table names here are a fixed application allowlist.
        for table_name in (
            "edited_content",
            "feedback",
            "humanized_history",
            "plagiarism_history",
            "saved_documents",
        ):
            db.session.execute(
                text(f"""
                    DELETE FROM {table_name}
                    WHERE user_id = :uid
                       OR (user_id IS NULL AND user_email = :email)
                """),
                parameters,
            )


        db.session.execute(
            text("""
                DELETE FROM generated_content
                WHERE user_id = :uid
                   OR (user_id IS NULL AND user_email = :email)
            """),
            parameters,
        )

        # CASCADE also removes notifications, user warnings,
        # moderation events, review cases, deletion requests
        # and deletion rate limits.
        result = db.session.execute(
            text("""
                DELETE FROM users
                WHERE id = :uid
            """),
            {"uid": user.id},
        )

        if result.rowcount != 1:
            raise AccountError(
                "Account deletion could not be completed.",
                409,
            )

        # All database deletions succeed or roll back together.
        db.session.commit()

    except Exception:
        db.session.rollback()
        raise

    # The database profile photo was removed with the user row.
    # Clean up an older local upload if one exists.
    _remove_old_profile_file(picture_path)

    email_sent = False

    try:
        from app import mail

        sender = (
            current_app.config.get("MAIL_DEFAULT_SENDER")
            or current_app.config.get("MAIL_USERNAME")
        )

        if sender:
            message = Message(
                subject="Your PFCG AI account has been deleted",
                sender=sender,
                recipients=[email],
            )

            message.body = (
                f"Hello {name},\n\n"
                "Your PFCG AI account has been permanently deleted.\n"
                "Your profile photo, content and associated reports "
                "have been removed.\n\n"
                "You can no longer sign in using this account.\n\n"
                "PFCG AI"
            )

            mail.send(message)
            email_sent = True

    except Exception:
        # Deletion already succeeded. A mail failure must not
        # report the account deletion itself as failed.
        current_app.logger.exception(
            "Unable to send account deletion confirmation email"
        )

    return {"email_sent": email_sent}