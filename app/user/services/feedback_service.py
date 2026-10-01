from sqlalchemy import text

from app.database import db


# ============================================================
# CREATE FEEDBACK
# ============================================================

def create_feedback(
    user_email,
    feedback_type,
    subject,
    message,
    rating
):

    query = text("""
        INSERT INTO feedback
        (
            user_id,
            user_email,
            feedback_type,
            subject,
            message,
            rating,
            status
        )
        SELECT
            id,
            email,
            :feedback_type,
            :subject,
            :message,
            :rating,
            'New'
        FROM users
        WHERE LOWER(email) = LOWER(:user_email)
        LIMIT 1
    """)

    try:

        result = db.session.execute(
            query,
            {
                "user_email": user_email,
                "feedback_type": feedback_type,
                "subject": subject,
                "message": message,
                "rating": rating
            }
        )

        if result.rowcount == 0:

            db.session.rollback()

            raise ValueError(
                "Registered user not found for feedback."
            )

        db.session.commit()

        return result.lastrowid

    except Exception:

        db.session.rollback()

        raise
# ============================================================
# GET USER FEEDBACK
# ============================================================

def get_user_feedback(user_email):

    query = text("""
        SELECT
            id,
            user_email,
            feedback_type,
            subject,
            message,
            rating,
            status,
            admin_reply,
            created_at
        FROM feedback
        WHERE user_email = :user_email
        ORDER BY id DESC
    """)

    result = db.session.execute(
        query,
        {
            "user_email": user_email
        }
    )

    rows = result.mappings().all()

    feedback = []

    for row in rows:

        feedback.append({
            "id": row["id"],
            "feedback_type": row["feedback_type"],
            "subject": row["subject"],
            "message": row["message"],
            "rating": row["rating"],
            "status": row["status"],
            "admin_reply": row["admin_reply"],
            "created_at": (
                row["created_at"].strftime("%Y-%m-%d %H:%M:%S")
                if row["created_at"]
                else None
            )
        })

    return feedback


# ============================================================
# GET LATEST USER FEEDBACK
# ============================================================

def get_latest_user_feedback(user_email):

    query = text("""
        SELECT
            id,
            user_email,
            feedback_type,
            subject,
            message,
            rating,
            status,
            admin_reply,
            created_at
        FROM feedback
        WHERE user_email = :user_email
        ORDER BY id DESC
        LIMIT 1
    """)

    result = db.session.execute(
        query,
        {
            "user_email": user_email
        }
    )

    row = result.mappings().first()

    if not row:
        return None

    return {
        "id": row["id"],
        "feedback_type": row["feedback_type"],
        "subject": row["subject"],
        "message": row["message"],
        "rating": row["rating"],
        "status": row["status"],
        "admin_reply": row["admin_reply"],
        "created_at": (
            row["created_at"].strftime("%Y-%m-%d %H:%M:%S")
            if row["created_at"]
            else None
        )
    }


# ============================================================
# ADMIN - GET ALL FEEDBACK
# ============================================================

def get_all_feedback():

    query = text("""
        SELECT
            id,
            user_email,
            feedback_type,
            subject,
            message,
            rating,
            status,
            admin_reply,
            created_at
        FROM feedback
        ORDER BY id DESC
    """)

    result = db.session.execute(query)

    rows = result.mappings().all()

    feedback = []

    for row in rows:

        feedback.append({
            "id": row["id"],
            "user_email": row["user_email"],
            "feedback_type": row["feedback_type"],
            "subject": row["subject"],
            "message": row["message"],
            "rating": row["rating"],
            "status": row["status"],
            "admin_reply": row["admin_reply"],
            "created_at": (
                row["created_at"].strftime("%Y-%m-%d %H:%M:%S")
                if row["created_at"]
                else None
            )
        })

    return feedback


# ============================================================
# ADMIN - UPDATE FEEDBACK
# ============================================================

def update_feedback(
    feedback_id,
    status,
    admin_reply
):

    query = text("""
        UPDATE feedback
        SET
            status = :status,
            admin_reply = :admin_reply
        WHERE id = :feedback_id
    """)

    result = db.session.execute(
        query,
        {
            "feedback_id": feedback_id,
            "status": status,
            "admin_reply": admin_reply
        }
    )

    db.session.commit()

    return result.rowcount > 0


# ============================================================
# ADMIN - DELETE FEEDBACK
# ============================================================

def delete_feedback(feedback_id):

    query = text("""
        DELETE FROM feedback
        WHERE id = :feedback_id
    """)

    result = db.session.execute(
        query,
        {
            "feedback_id": feedback_id
        }
    )

    db.session.commit()

    return result.rowcount > 0