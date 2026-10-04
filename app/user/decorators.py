from datetime import datetime
from functools import wraps
from math import ceil

from flask import (
    current_app,
    jsonify,
    redirect,
    request,
    session,
    url_for,
)

from app.database import db
from app.models import User

from app.user.services.account_suspension_service import (
    sync_account_suspension,
)


def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")

        is_api_request = (
            request.is_json
            or "/api/" in request.path
            or request.accept_mimetypes.best
            in {"application/json", "application/x-ndjson"}
        )

        def deny_access(
            message,
            status_code,
            account_status=None,
            suspended_until=None,
        ):
            session.clear()

            if is_api_request:
                return jsonify(
                    success=False,
                    message=message,
                    account_status=account_status,
                    suspended_until=(
                        suspended_until.isoformat() + "Z"
                        if suspended_until
                        else None
                    ),
                ), status_code

            return redirect(
                url_for(
                    "auth.login",
                    account_status=account_status,
                )
            )

        if not user_id:
            return deny_access(
                "Your session has expired. Please sign in again.",
                401,
            )

        try:
            sync_account_suspension(user_id)

            user = db.session.get(
                User,
                user_id,
                populate_existing=True,
            )

        except Exception:
            db.session.rollback()
            current_app.logger.exception(
                "Unable to check account suspension"
            )

            message = (
                "Unable to check account status. Please try again."
            )

            if is_api_request:
                return jsonify(
                    success=False,
                    message=message,
                ), 503

            return message, 503

        if user is None:
            return deny_access(
                "Account not found. Please sign in again.",
                401,
            )

        now = datetime.utcnow()
        user_status = (
            user.status or "active"
        ).strip().lower()

        if user_status != "active":
            if (
                user_status == "suspended"
                and user.suspended_until is not None
                and user.suspended_until > now
            ):
                seconds = (
                    user.suspended_until - now
                ).total_seconds()

                minutes = max(1, ceil(seconds / 60))

                message = (
                    "Your account is temporarily suspended. "
                    f"Try again in {minutes} minute(s)."
                )

                if user.status_reason:
                    message += f" Reason: {user.status_reason}"
            else:
                message = {
                    "suspended": "Your account is suspended.",
                    "blocked": "Your account is blocked.",
                    "pending_deletion": (
                        "Your account is scheduled for deletion."
                    ),
                    "deleted": (
                        "This account is no longer available."
                    ),
                }.get(
                    user_status,
                    "Your account is unavailable.",
                )

            return deny_access(
                message,
                403,
                account_status=user_status,
                suspended_until=user.suspended_until,
            )

        # Generator restrictions are checked by Generate/Humanize.
        # Other pages remain accessible to active accounts.
        return function(*args, **kwargs)

    return wrapper