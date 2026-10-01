from functools import wraps

from flask import (
    session,
    redirect,
    url_for
)

from app.models import User


# ============================================================
# USER LOGIN AND ACCOUNT-STATUS CHECK
# ============================================================

def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        # ====================================================
        # SESSION CHECK
        # ====================================================

        user_id = session.get(
            "user_id"
        )

        if not user_id:

            session.clear()

            return redirect(
                url_for("auth.login")
            )


        # ====================================================
        # GET CURRENT USER
        # ====================================================

        user = User.query.filter_by(
            id=user_id
        ).first()


        # User database se delete ho chuka ho
        if not user:

            session.clear()

            return redirect(
                url_for("auth.login")
            )


        # ====================================================
        # ACCOUNT STATUS CHECK
        # ====================================================

        user_status = (
            getattr(
                user,
                "status",
                "active"
            )
            or "active"
        ).strip().lower()


        blocked_statuses = {
            "blocked",
            "pending_deletion",
            "deleted",
        }

        if user_status in blocked_statuses:
            session.clear()
            return redirect(
                url_for(
                    "auth.login",
                    account_status=user_status,
                )
            )

   

        # ====================================================
        # ALLOW ACTIVE USER
        # ====================================================

        return function(
            *args,
            **kwargs
        )

    return wrapper