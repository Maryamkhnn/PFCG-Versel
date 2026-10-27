from datetime import datetime, timedelta

from flask import current_app
from flask_mail import Message
from sqlalchemy import text

from app.database import db


# ============================================================
# AUTOMATIC MODERATION RULES
# ============================================================

ATTEMPT_LIMIT = 3
ATTEMPT_WINDOW_HOURS = 24

RESTRICTION_HOURS = 1

SUSPENSION_THRESHOLD = 3
SUSPENSION_WINDOW_DAYS = 7
SUSPENSION_HOURS = 24


def _pkt_time(value):
    local_time = value + timedelta(hours=5)
    return local_time.strftime("%d %b %Y at %I:%M %p PKT")


def _add_notification(user_id, notification_type, title, message, now):
    """Insert inside the same transaction as the moderation action."""

    db.session.execute(
        text("""
            INSERT INTO user_notifications (
                user_id,
                notification_type,
                title,
                message,
                is_read,
                created_at
            )
            VALUES (
                :uid,
                :notification_type,
                :title,
                :message,
                0,
                :created
            )
        """),
        {
            "uid": user_id,
            "notification_type": notification_type,
            "title": title,
            "message": message,
            "created": now,
        },
    )


def _send_moderation_email(email, name, title, message):
    """
    Send only after the database transaction succeeds.
    Email failure must not undo a restriction or suspension.
    """

    try:
        # Local import avoids importing mail during module initialization.
        from app import mail

        sender = (
            current_app.config.get("MAIL_DEFAULT_SENDER")
            or current_app.config.get("MAIL_USERNAME")
        )

        if not email or not sender:
            raise RuntimeError(
                "Moderation email recipient or sender is missing."
            )

        mail_message = Message(
            subject=f"PFCG AI — {title}",
            sender=sender,
            recipients=[email],
        )

        mail_message.body = (
            f"Hello {name or 'User'},\n\n"
            f"{message}\n\n"
            "If you believe this action was incorrect, "
            "please contact the PFCG AI administrator.\n\n"
            "Regards,\n"
            "PFCG AI Team"
        )

        mail.send(mail_message)
        return True

    except Exception:
        current_app.logger.exception(
            "Unable to send moderation email"
        )
        return False


def record_blocked_attempt(user_id, category):
    """
    Record one blocked-topic attempt.

    Three fresh attempts within 24 hours:
        Restrict Generate, Regenerate and Humanize for one hour.

    Three new restriction events within seven days:
        Suspend the account for 24 hours and flag it for review.

    Restrictions already used for a suspension are not reused
    to trigger another suspension.
    """

    email_details = None

    try:
        # Serialize moderation requests for this user.
        user = db.session.execute(
            text("""
                SELECT
                    id,
                    name,
                    email,
                    role,
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
            raise ValueError("User account not found.")

        now = datetime.utcnow()
        account_status = (user["status"] or "active").strip().lower()

        # Never add attempts while the account is unavailable.
        if account_status != "active":
            db.session.commit()

            return {
                "action": "unavailable",
                "account_status": account_status,
                "until": user["suspended_until"],
                "message": "Your account is currently unavailable.",
            }

        current_until = user["generator_restricted_until"]

        # Retries and simultaneous requests cannot extend the timer.
        if current_until is not None and current_until > now:
            db.session.commit()

            return {
                "action": "restricted",
                "until": current_until,
                "message": (
                    "Content generation and humanization are restricted. "
                    f"Available again on {_pkt_time(current_until)}."
                ),
            }

        category = (
            str(category or "Restricted topic").strip()
            or "Restricted topic"
        )[:255]

        inserted = db.session.execute(
            text("""
                INSERT INTO blocked_topic_attempts (
                    user_id,
                    category,
                    created_at
                )
                VALUES (:uid, :category, :created)
            """),
            {
                "uid": user_id,
                "category": category,
                "created": now,
            },
        )

        attempt_id = inserted.lastrowid

        # Admin tests are logged but do not restrict admin accounts.
        if (user["role"] or "user").strip().lower() == "admin":
            db.session.commit()

            return {
                "action": "warning",
                "message": "This topic is not allowed.",
            }

        last_attempt_id = db.session.execute(
            text("""
                SELECT last_attempt_id
                FROM generator_restriction_events
                WHERE user_id = :uid
                ORDER BY id DESC
                LIMIT 1
            """),
            {"uid": user_id},
        ).scalar_one_or_none() or 0

        # Only attempts after the previous restriction are fresh.
        attempts = db.session.execute(
            text("""
                SELECT COUNT(*)
                FROM blocked_topic_attempts
                WHERE user_id = :uid
                  AND id > :last_attempt_id
                  AND created_at >= :since
            """),
            {
                "uid": user_id,
                "last_attempt_id": last_attempt_id,
                "since": now - timedelta(hours=ATTEMPT_WINDOW_HOURS),
            },
        ).scalar_one()

        if attempts < ATTEMPT_LIMIT:
            db.session.commit()

            return {
                "action": "warning",
                "attempt_count": int(attempts),
                "message": (
                    "This topic is not allowed. "
                    f"Blocked attempt {attempts} of {ATTEMPT_LIMIT} "
                    "within 24 hours. "
                    "The third attempt temporarily restricts "
                    "content generation and humanization."
                ),
            }

        restriction_until = now + timedelta(hours=RESTRICTION_HOURS)

        restriction = db.session.execute(
            text("""
                INSERT INTO generator_restriction_events (
                    user_id,
                    last_attempt_id,
                    category,
                    started_at,
                    restricted_until
                )
                VALUES (
                    :uid,
                    :attempt_id,
                    :category,
                    :started,
                    :until
                )
            """),
            {
                "uid": user_id,
                "attempt_id": attempt_id,
                "category": category,
                "started": now,
                "until": restriction_until,
            },
        )

        restriction_id = restriction.lastrowid

        # Start a fresh escalation cycle after each suspension.
        last_suspension_trigger = db.session.execute(
            text("""
                SELECT COALESCE(MAX(trigger_restriction_id), 0)
                FROM account_suspension_events
                WHERE user_id = :uid
            """),
            {"uid": user_id},
        ).scalar_one()

        restriction_count = db.session.execute(
            text("""
                SELECT COUNT(*)
                FROM generator_restriction_events
                WHERE user_id = :uid
                  AND is_incorrect = 0
                  AND id > :last_trigger
                  AND started_at >= :since
            """),
            {
                "uid": user_id,
                "last_trigger": last_suspension_trigger,
                "since": now - timedelta(days=SUSPENSION_WINDOW_DAYS),
            },
        ).scalar_one()

        # Create or reopen an admin review case for the restriction.
        case = db.session.execute(
            text("""
                SELECT id
                FROM moderation_review_cases
                WHERE user_id = :uid
                FOR UPDATE
            """),
            {"uid": user_id},
        ).mappings().first()

        if case is None:
            db.session.execute(
                text("""
                    INSERT INTO moderation_review_cases (
                        user_id,
                        pending,
                        restriction_count,
                        flagged_at
                    )
                    VALUES (:uid, 1, :count, :flagged)
                """),
                {
                    "uid": user_id,
                    "count": restriction_count,
                    "flagged": now,
                },
            )
             
        else:
         db.session.execute(
        text("""
            UPDATE moderation_review_cases
            SET pending = 1,
                restriction_count = :count,
                flagged_at = :flagged,
                reviewed_at = NULL,
                reviewed_by = NULL,
                review_action = NULL,
                review_reason = NULL,
                last_reviewed_event_id = NULL
            WHERE id = :case_id
        """),
        {
            "count": restriction_count,
            "flagged": now,
            "case_id": case["id"],
        },
    )


        if restriction_count >= SUSPENSION_THRESHOLD:
            suspension_until = now + timedelta(hours=SUSPENSION_HOURS)

            reason = (
                "Three restrictions caused by repeated blocked-topic "
                "attempts within seven days."
            )

            db.session.execute(
                text("""
                    UPDATE users
                    SET status = 'suspended',
                        suspended_until = :until,
                        generator_restricted_until = NULL,
                        status_reason = :reason,
                        status_changed_at = :changed
                    WHERE id = :uid
                """),
                {
                    "uid": user_id,
                    "until": suspension_until,
                    "reason": reason,
                    "changed": now,
                },
            )

            db.session.execute(
                text("""
                    INSERT INTO account_suspension_events (
                        user_id,
                        trigger_restriction_id,
                        reason,
                        started_at,
                        suspended_until
                    )
                    VALUES (
                        :uid,
                        :trigger_id,
                        :reason,
                        :started,
                        :until
                    )
                """),
                {
                    "uid": user_id,
                    "trigger_id": restriction_id,
                    "reason": reason,
                    "started": now,
                    "until": suspension_until,
                },
            )

            case = db.session.execute(
                text("""
                    SELECT id
                    FROM moderation_review_cases
                    WHERE user_id = :uid
                    FOR UPDATE
                """),
                {"uid": user_id},
            ).mappings().first()

            if case is None:
                db.session.execute(
                    text("""
                        INSERT INTO moderation_review_cases (
                            user_id,
                            pending,
                            restriction_count,
                            flagged_at
                        )
                        VALUES (:uid, 1, :count, :flagged)
                    """),
                    {
                        "uid": user_id,
                        "count": restriction_count,
                        "flagged": now,
                    },
                )
            else:
                # Reopen the existing case instead of duplicating it.
                db.session.execute(
                    text("""
                       UPDATE moderation_review_cases
SET pending = 1,
    restriction_count = :count,
    flagged_at = :flagged,
    reviewed_at = NULL,
    reviewed_by = NULL,
    review_action = NULL,
    review_reason = NULL
WHERE user_id = :uid
                    """),
                    {
                        "uid": user_id,
                        "count": restriction_count,
                        "flagged": now,
                    },
                )

            title = "Account temporarily suspended"

            message = (
                "Your PFCG AI account has been automatically suspended "
                f"for {SUSPENSION_HOURS} hours.\n"
                f"Reason: {reason}\n"
                "Affected access: All account features.\n"
                f"Access becomes available again on "
                f"{_pkt_time(suspension_until)}.\n"
                "Your case has been flagged for administrator review."
            )

            notification_type = "suspend"

            result = {
                "action": "suspended",
                "account_status": "suspended",
                "until": suspension_until,
                "restriction_count": int(restriction_count),
                "message": message,
            }

        else:
            db.session.execute(
                text("""
                    UPDATE users
                    SET generator_restricted_until = :until
                    WHERE id = :uid
                """),
                {
                    "uid": user_id,
                    "until": restriction_until,
                },
            )

            title = "Generation and humanization restricted"

            message = (
                "Content generation and humanization have been "
                f"automatically restricted for {RESTRICTION_HOURS} hour.\n"
                "Reason: Three blocked-topic attempts within 24 hours.\n"
                "Affected features: Generate, Regenerate and Humanize.\n"
                f"Available again on {_pkt_time(restriction_until)}.\n"
                "Login, My Content, editor, SEO and saved-content "
                "export remain available."
            )

            notification_type = "generator_restricted"

            result = {
                "action": "restricted",
                "until": restriction_until,
                "restriction_count": int(restriction_count),
                "message": message,
            }

        _add_notification(
            user_id,
            notification_type,
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

        # History, account status and notification succeed together.
        db.session.commit()

    except Exception:
        db.session.rollback()
        current_app.logger.exception(
            "Automatic moderation failed"
        )
        raise

    # Do not hold a database lock during email delivery.
    if email_details is not None:
        result["email_sent"] = _send_moderation_email(*email_details)

    return result
class ModerationReviewError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status
def review_moderation_case(
    case_id,
    admin_id,
    action,
    reason,
    expected_suspension_id,
    expected_restriction_id=None,
):
    """
    Review an automatic generator restriction or account suspension.

    confirm:
        Close the review without extending the restriction.

    incorrect:
        Remove only the matching current restriction.
        Preserve newer or unrelated restrictions and event history.
    """

    if action not in {"confirm", "incorrect"}:
        raise ModerationReviewError("Invalid review action.")

    if not isinstance(reason, str):
        raise ModerationReviewError("Please enter a review reason.")

    reason = reason.strip()

    if not 10 <= len(reason) <= 1000:
        raise ModerationReviewError(
            "Review reason must contain 10 to 1000 characters."
        )

    def valid_event_id(value):
        return (
            isinstance(value, int)
            and not isinstance(value, bool)
            and value > 0
        )

    has_suspension = valid_event_id(expected_suspension_id)
    has_restriction = valid_event_id(expected_restriction_id)

    if (
        has_suspension == has_restriction
        or (
            expected_suspension_id is not None
            and not has_suspension
        )
        or (
            expected_restriction_id is not None
            and not has_restriction
        )
    ):
        raise ModerationReviewError(
            "Please reopen the case before reviewing it."
        )

    try:
        administrator = db.session.execute(
            text("""
                SELECT id, email, role, status
                FROM users
                WHERE id = :admin_id
            """),
            {"admin_id": admin_id},
        ).mappings().first()

        if (
            administrator is None
            or (administrator["role"] or "").strip().lower()
                != "admin"
            or (administrator["status"] or "active").strip().lower()
                != "active"
        ):
            raise ModerationReviewError(
                "Administrator access is required.",
                403,
            )

        case_user_id = db.session.execute(
            text("""
                SELECT user_id
                FROM moderation_review_cases
                WHERE id = :case_id
            """),
            {"case_id": case_id},
        ).scalar_one_or_none()

        if case_user_id is None:
            raise ModerationReviewError(
                "Review case not found.",
                404,
            )

        # Keep the existing lock order: user, then case.
        user = db.session.execute(
            text("""
                SELECT
                    id,
                    name,
                    email,
                    role,
                    status,
                    suspended_until,
                    status_reason,
                    generator_restricted_until
                FROM users
                WHERE id = :uid
                FOR UPDATE
            """),
            {"uid": case_user_id},
        ).mappings().first()

        case = db.session.execute(
            text("""
                SELECT id, user_id, pending, flagged_at
                FROM moderation_review_cases
                WHERE id = :case_id
                FOR UPDATE
            """),
            {"case_id": case_id},
        ).mappings().first()

        if user is None or case is None:
            raise ModerationReviewError(
                "Review case not found.",
                404,
            )

        if not case["pending"]:
            raise ModerationReviewError(
                "This case has already been reviewed. Refresh the page.",
                409,
            )

        if (user["role"] or "user").strip().lower() == "admin":
            raise ModerationReviewError(
                "Administrator accounts cannot be reviewed here.",
                403,
            )

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
            {"uid": user["id"]},
        ).mappings().first()

        matching_case_suspension = (
            suspension is not None
            and suspension["started_at"] == case["flagged_at"]
        )

        now = datetime.utcnow()
        status = (user["status"] or "active").strip().lower()

        suspension_cancelled = False
        restriction_cancelled = False

        if has_suspension:
            if (
                not matching_case_suspension
                or suspension["id"] != expected_suspension_id
            ):
                raise ModerationReviewError(
                    "This case has changed. Reopen it and review again.",
                    409,
                )

            case_type = "account_suspended"
            event_id = suspension["trigger_restriction_id"]
            event_description = f"Suspension #{suspension['id']}"
            subject = "automatic account suspension"

            if action == "incorrect":
                matching_current_suspension = (
                    status == "suspended"
                    and user["suspended_until"]
                        == suspension["suspended_until"]
                    and user["status_reason"] == suspension["reason"]
                )

                if status != "active" and not matching_current_suspension:
                    raise ModerationReviewError(
                        "The account has a different restriction. "
                        "This review cannot remove it.",
                        409,
                    )

                if matching_current_suspension:
                    db.session.execute(
                        text("""
                            UPDATE users
                            SET status = 'active',
                                suspended_until = NULL,
                                status_reason = NULL,
                                status_changed_at = :changed
                            WHERE id = :uid
                        """),
                        {
                            "uid": user["id"],
                            "changed": now,
                        },
                    )

                    suspension_cancelled = True
                    status = "active"

                outcome = (
                    "That account suspension has been cancelled."
                    if suspension_cancelled
                    else "Your account was already active."
                )

        else:
            # A suspension case cannot be reviewed as a generator case.
            if matching_case_suspension:
                raise ModerationReviewError(
                    "This case has changed. Reopen it and review again.",
                    409,
                )

            restriction = db.session.execute(
                text("""
                    SELECT
                        id,
                        started_at,
                        restricted_until
                    FROM generator_restriction_events
                    WHERE user_id = :uid
                    ORDER BY id DESC
                    LIMIT 1
                """),
                {"uid": user["id"]},
            ).mappings().first()

            if (
                restriction is None
                or restriction["id"] != expected_restriction_id
                or restriction["started_at"] != case["flagged_at"]
            ):
                raise ModerationReviewError(
                    "This case has changed. Reopen it and review again.",
                    409,
                )

            case_type = "generator_restricted"
            event_id = restriction["id"]
            event_description = f"Generator restriction #{event_id}"
            subject = "automatic generator restriction"

            if action == "incorrect":
                    db.session.execute(
                    text("""
                        UPDATE generator_restriction_events
                        SET is_incorrect = 1
                        WHERE id = :restriction_id
                          AND user_id = :uid
                    """),
                    {
                        "restriction_id": restriction["id"],
                        "uid": user["id"],
                    },
                )
            current_until = user["generator_restricted_until"]

            matching_current_restriction = (
                    current_until is not None
                    and current_until == restriction["restricted_until"]
                )

            if (
                    current_until is not None
                    and current_until > now
                    and not matching_current_restriction
                ):
                    raise ModerationReviewError(
                        "The user has a different generator restriction. "
                        "This review cannot remove it.",
                        409,
                    )

            if matching_current_restriction:
                    db.session.execute(
                        text("""
                            UPDATE users
                            SET generator_restricted_until = NULL
                            WHERE id = :uid
                              AND generator_restricted_until = :until
                        """),
                        {
                            "uid": user["id"],
                            "until": restriction["restricted_until"],
                        },
                    )

                    restriction_cancelled = True

            outcome = (
                    "That generator restriction has been removed."
                    if restriction_cancelled
                    else "That generator restriction is no longer active."
                )

            if status != "active":
                    outcome += (
                        " Your account status remains unchanged."
                    )

        title = "Moderation review completed"

        if action == "incorrect":
            message = (
                f"An administrator reviewed your {subject} "
                f"and found it incorrect. {outcome} "
                f"Review reason: {reason}"
            )
        else:
            message = (
                f"An administrator reviewed your {subject} "
                "and confirmed the violation records. "
                f"Review reason: {reason}. "
                "This review does not add another restriction "
                "or extend the original expiry."
            )

        db.session.execute(
            text("""
                UPDATE moderation_review_cases
                SET pending = 0,
                    reviewed_at = :reviewed,
                    reviewed_by = :admin_id,
                    review_action = :action,
                    review_reason = :reason,
                    last_reviewed_event_id = :event_id
                WHERE id = :case_id
            """),
            {
                "case_id": case_id,
                "reviewed": now,
                "admin_id": administrator["id"],
                "action": action,
                "reason": reason,
                "event_id": event_id,
            },
        )

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
                    :action,
                    'Moderation Review',
                    :details,
                    :created
                )
            """),
            {
                "admin_id": administrator["id"],
                "admin_email": administrator["email"],
                "action": (
                    f"Confirmed {subject}"
                    if action == "confirm"
                    else f"Marked {subject} incorrect"
                ),
                "details": (
                    f"Case #{case_id}; User #{user['id']}; "
                    f"{event_description}; "
                    f"Suspension cancelled: {suspension_cancelled}; "
                    f"Generator restriction removed: "
                    f"{restriction_cancelled}; "
                    f"Reason: {reason}"
                ),
                "created": now,
            },
        )

        _add_notification(
            user["id"],
            "info",
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

    email_sent = _send_moderation_email(*email_details)

    return {
        "case_id": case_id,
        "case_type": case_type,
        "action": action,
        "account_status": status,
        "suspension_cancelled": suspension_cancelled,
        "restriction_cancelled": restriction_cancelled,
        "email_sent": email_sent,
        "message": "Review saved successfully.",
    }