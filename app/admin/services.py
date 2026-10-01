from sqlalchemy import text
from app.database import db
from app.models import User


# =====================================================
# DASHBOARD DATA
# =====================================================

def get_dashboard_data():

    # -------------------------------
    # TOTAL USERS
    # -------------------------------

    total_users = db.session.execute(
        text("""
            SELECT COUNT(*)
            FROM users
            WHERE role = 'user'
        """)
    ).scalar() or 0


    # -------------------------------
    # TOTAL GENERATED CONTENT
    # -------------------------------

    total_content = db.session.execute(
        text("""
            SELECT COUNT(*)
            FROM generated_content
        """)
    ).scalar() or 0


    # -------------------------------
    # TOTAL SEO REPORTS
    # -------------------------------

    total_seo = db.session.execute(
        text("""
            SELECT COUNT(*)
            FROM seo_history
        """)
    ).scalar() or 0


    # -------------------------------
    # TOTAL FEEDBACK
    # -------------------------------

    total_feedbacks = db.session.execute(
        text("""
            SELECT COUNT(*)
            FROM feedback
        """)
    ).scalar() or 0


    # -------------------------------
    # TOTAL HUMANIZED
    # -------------------------------

    total_humanized = db.session.execute(
        text("""
            SELECT COUNT(*)
            FROM humanized_history
        """)
    ).scalar() or 0


    # -------------------------------
    # TOTAL PLAGIARISM
    # -------------------------------

    total_plagiarism = db.session.execute(
        text("""
            SELECT COUNT(*)
            FROM plagiarism_history
        """)
    ).scalar() or 0


    # -------------------------------
    # RECENT GENERATED CONTENT
    # -------------------------------

    recent_content = db.session.execute(
        text("""
            SELECT
                user_email,
                topic,
                word_count,
                content_type,
                created_at
            FROM generated_content
            ORDER BY created_at DESC
            LIMIT 5
        """)
    ).mappings().all()


    # -------------------------------
    # RECENT SEO
    # -------------------------------

    recent_seo = db.session.execute(
        text("""
            SELECT
                user_email,
                content_topic,
                seo_score,
                created_at
            FROM seo_history
            ORDER BY created_at DESC
            LIMIT 5
        """)
    ).mappings().all()


    # -------------------------------
    # RECENT HUMANIZED
    # -------------------------------

    recent_humanized = db.session.execute(
        text("""
            SELECT
                user_email,
                word_count,
                created_at
            FROM humanized_history
            ORDER BY created_at DESC
            LIMIT 5
        """)
    ).mappings().all()


    # -------------------------------
    # RECENT PLAGIARISM
    # -------------------------------

    recent_plagiarism = db.session.execute(
        text("""
            SELECT *
            FROM plagiarism_history
            ORDER BY created_at DESC
            LIMIT 5
        """)
    ).mappings().all()


    # -------------------------------
    # RECENT FEEDBACK
    # -------------------------------

    recent_feedback = db.session.execute(
        text("""
            SELECT
                user_email,
                subject,
                rating,
                created_at
            FROM feedback
            ORDER BY created_at DESC
            LIMIT 5
        """)
    ).mappings().all()

    blocked_alerts = db.session.execute(
        text("""
            SELECT
                u.id AS user_id,
                u.email,
                COUNT(*) AS attempts,
                MAX(b.created_at) AS last_attempt
            FROM blocked_topic_attempts AS b
            JOIN users AS u ON u.id = b.user_id
            WHERE b.created_at >= NOW() - INTERVAL 24 HOUR
            GROUP BY u.id, u.email
            HAVING COUNT(*) >= 3
            ORDER BY last_attempt DESC
            LIMIT 20
        """)
    ).mappings().all()
    return {
        "total_users": total_users,
        "total_content": total_content,
        "total_seo": total_seo,
        "total_feedbacks": total_feedbacks,
        "total_humanized": total_humanized,
        "total_plagiarism": total_plagiarism,
        "recent_content": recent_content,
        "recent_seo": recent_seo,
        "recent_humanized": recent_humanized,
        "recent_plagiarism": recent_plagiarism,
        "recent_feedback": recent_feedback,
        "blocked_alerts": blocked_alerts,
    }

# =====================================================
# GET ALL FEEDBACK
# =====================================================

def get_feedback():

    feedbacks = db.session.execute(
        text("""
            SELECT
                id,
                user_email,
                feedback_type,
                subject,
                message,
                rating,
                COALESCE(
                    status,
                    'New'
                ) AS status,
                admin_reply,
                created_at

            FROM feedback

            ORDER BY created_at DESC
        """)
    ).mappings().all()

    return feedbacks


# =====================================================
# MANAGE USERS
# =====================================================

def get_users(page=1, per_page=10):

    return User.query.filter_by(
        role="user"
    ).order_by(
        User.id.desc()
    ).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

def get_user_activity_counts(user_id, user_email):

    try:
        generated_count = db.session.execute(
            text("""
                SELECT COUNT(*)
                FROM generated_content
                WHERE user_id = :user_id
                   OR user_email = :user_email
            """),
            {
                "user_id": user_id,
                "user_email": user_email
            }
        ).scalar() or 0

        humanized_count = db.session.execute(
            text("""
                SELECT COUNT(*)
                FROM humanized_history
                WHERE user_id = :user_id
                   OR user_email = :user_email
            """),
            {
                "user_id": user_id,
                "user_email": user_email
            }
        ).scalar() or 0

        plagiarism_count = db.session.execute(
            text("""
                SELECT COUNT(*)
                FROM plagiarism_history
                WHERE user_id = :user_id
                   OR user_email = :user_email
            """),
            {
                "user_id": user_id,
                "user_email": user_email
            }
        ).scalar() or 0

        seo_count = db.session.execute(
            text("""
                SELECT COUNT(*)
                FROM seo_history
                WHERE user_email = :user_email
            """),
            {
                "user_email": user_email
            }
        ).scalar() or 0

        feedback_count = db.session.execute(
            text("""
                SELECT COUNT(*)
                FROM feedback
                WHERE user_email = :user_email
            """),
            {
                "user_email": user_email
            }
        ).scalar() or 0

        return {
            "generated": generated_count,
            "humanized": humanized_count,
            "plagiarism": plagiarism_count,
            "seo": seo_count,
            "feedback": feedback_count,
            "total": (
                generated_count
                + humanized_count
                + plagiarism_count
                + seo_count
                + feedback_count
            )
        }

    except Exception as e:

        print("GET USER ACTIVITY COUNTS ERROR:", e)

        return {
            "generated": 0,
            "humanized": 0,
            "plagiarism": 0,
            "seo": 0,
            "feedback": 0,
            "total": 0
        }
# =====================================================
# GENERATED CONTENT
# =====================================================

def get_generated_content(page=1, per_page=10):

    query = db.session.execute(
        text("""
            SELECT
                id,
                user_email,
                topic,
                content,
                word_count,
                content_type,
                created_at
            FROM generated_content
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        {
            "limit": per_page,
            "offset": (page - 1) * per_page
        }
    )

    contents = query.mappings().all()


    total = db.session.execute(
        text("""
            SELECT COUNT(*)
            FROM generated_content
        """)
    ).scalar() or 0


    return contents, total


# =====================================================
# SEO REPORTS
# =====================================================

def get_seo_reports():

    return db.session.execute(
        text("""
            SELECT
                id,
                user_email,
                content_topic,
                word_count,
                seo_score,
                readability_score,
                keyword_density,
                keyword_count,
                seo_status,
                content_id,
                created_at
            FROM seo_history
            ORDER BY created_at DESC
        """)
    ).mappings().all()

# =====================================================
# MARK FEEDBACK AS REVIEWED
# =====================================================

def mark_feedback_reviewed(feedback_id):

    feedback_exists = db.session.execute(
        text("""
            SELECT id
            FROM feedback
            WHERE id = :feedback_id
        """),
        {
            "feedback_id": feedback_id
        }
    ).scalar()

    if not feedback_exists:
        return False

    db.session.execute(
        text("""
            UPDATE feedback

            SET status = 'Reviewed'

            WHERE id = :feedback_id

            AND LOWER(
                COALESCE(status, 'new')
            ) = 'new'
        """),
        {
            "feedback_id": feedback_id
        }
    )

    db.session.commit()

    return True


def get_reports_data():

    # =====================================================
    # SUMMARY COUNTS
    # =====================================================

    total_seo = db.session.execute(
        text("""
            SELECT COUNT(*)
            FROM seo_history
        """)
    ).scalar() or 0


    # AI GENERATED CONTENT PLAGIARISM
    total_ai_plagiarism = db.session.execute(
    text("""
        SELECT COUNT(*)
        FROM plagiarism_history
        WHERE UPPER(TRIM(check_type)) IN ('AI', 'AI_CONTENT')
    """)
).scalar() or 0


    # =====================================================
# HUMANIZED CONTENT PLAGIARISM
# =====================================================

    total_humanized_plagiarism = db.session.execute(
    text("""
        SELECT COUNT(*)
        FROM plagiarism_history
        WHERE UPPER(TRIM(check_type)) = 'HUMANIZED'
    """)
    ).scalar() or 0

    # FEEDBACK

    total_feedback = db.session.execute(
        text("""
            SELECT COUNT(*)
            FROM feedback
        """)
    ).scalar() or 0


    # =====================================================
    # AVERAGES
    # =====================================================

    average_seo = db.session.execute(
        text("""
            SELECT ROUND(AVG(seo_score), 1)
            FROM seo_history
            WHERE seo_score IS NOT NULL
        """)
    ).scalar() or 0


    average_rating = db.session.execute(
        text("""
            SELECT ROUND(AVG(rating), 1)
            FROM feedback
            WHERE rating IS NOT NULL
        """)
    ).scalar() or 0


    # =====================================================
    # SEO REPORTS
    # =====================================================

    recent_seo = db.session.execute(
        text("""
            SELECT
                id,
                user_email,
                content_topic,
                word_count,
                seo_score,
                readability_score,
                keyword_density,
                keyword_count,
                seo_status,
                content_id,
                created_at
            FROM seo_history
            ORDER BY created_at DESC
        """)
    ).mappings().all()


    # =====================================================
    # AI CONTENT PLAGIARISM REPORTS
    # =====================================================

    recent_ai_plagiarism = db.session.execute(
        text("""
            SELECT
                id,
                user_id,
                user_email,
                score,
                topic,
                content,
                matched_sources,
                check_type,
                created_at
            FROM plagiarism_history
             WHERE UPPER(TRIM(check_type)) IN ('AI', 'AI_CONTENT')
            ORDER BY created_at DESC
        """)
    ).mappings().all()


    # =====================================================
    # HUMANIZED CONTENT PLAGIARISM REPORTS
    # =====================================================

    recent_humanized_plagiarism = db.session.execute(
        text("""
            SELECT
                id,
                user_id,
                user_email,
                score,
                topic,
                content,
                matched_sources,
                check_type,
                created_at
            FROM plagiarism_history
            WHERE UPPER(TRIM(check_type)) = 'HUMANIZED'
            ORDER BY created_at DESC
        """)
    ).mappings().all()


    # =====================================================
    # FEEDBACK REPORTS
    # =====================================================

    recent_feedback = db.session.execute(
        text("""
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
            ORDER BY created_at DESC
        """)
    ).mappings().all()


    # =====================================================
    # RETURN
    # =====================================================

    return {

        "total_seo": total_seo,

        "total_ai_plagiarism": total_ai_plagiarism,

        "total_humanized_plagiarism":
            total_humanized_plagiarism,

        "total_feedback": total_feedback,

        "average_seo": average_seo,

        "average_rating": average_rating,

        "recent_seo": recent_seo,

        "recent_ai_plagiarism":
            recent_ai_plagiarism,

        "recent_humanized_plagiarism":
            recent_humanized_plagiarism,

        "recent_feedback": recent_feedback
    }
# =====================================================
# GET SINGLE USER
# =====================================================

def get_user_by_id(user_id):

    return User.query.filter_by(
        id=user_id,
        role="user"
    ).first()


# =====================================================
# UPDATE USER
# =====================================================

def update_user(user_id, data):

    user = User.query.filter_by(
        id=user_id,
        role="user"
    ).first()

    if not user:
        return None


    # -------------------------------
    # UPDATE NAME
    # -------------------------------

    if "name" in data:
        user.name = data["name"].strip()


    # -------------------------------
    # UPDATE EMAIL
    # -------------------------------

    if "email" in data:
        user.email = data["email"].strip()


    # -------------------------------
    # UPDATE USERNAME
    # -------------------------------

    if "username" in data:
        user.username = data["username"].strip()


    db.session.commit()

    return user


# =====================================================
# MODERATE USER ACCOUNT
# =====================================================

def moderate_user_account(
    user_id,
    admin_id,
    admin_email,
    action,
    reason,
    ip_address=None
):

    allowed_actions = {
        "warn",
        "suspend",
        "reactivate",
        "schedule_delete",
        "cancel_delete"
    }

    action = str(action or "").strip().lower()
    reason = str(reason or "").strip()

    if action not in allowed_actions:
        raise ValueError("Please choose a valid moderation action.")

    if len(reason) < 10:
        raise ValueError("Please provide a reason of at least 10 characters.")

    user = get_user_by_id(user_id)

    if not user:
        return None

    old_status = (user.status or "active").strip().lower()
    new_status = old_status

    titles = {
        "warn": "Account warning",
        "suspend": "Account suspended",
        "reactivate": "Account reactivated",
        "schedule_delete": "Account deletion scheduled",
        "cancel_delete": "Account deletion cancelled"
    }

    messages = {
        "warn": f"An administrator issued a warning: {reason}",
        "suspend": f"Your account has been suspended. Reason: {reason}",
        "reactivate": f"Your account has been reactivated. Note: {reason}",
        "schedule_delete": (
            "Your account is scheduled for deletion after 7 days. "
            f"Reason: {reason}"
        ),
        "cancel_delete": f"The scheduled account deletion was cancelled. Note: {reason}"
    }

    try:
        if action == "warn":
            db.session.execute(
                text("""
                    INSERT INTO user_warnings (user_id, admin_id, reason)
                    VALUES (:user_id, :admin_id, :reason)
                """),
                {
                    "user_id": user_id,
                    "admin_id": admin_id,
                    "reason": reason
                }
            )

        elif action == "suspend":
            new_status = "suspended"
            db.session.execute(
                text("""
                    UPDATE users
                    SET status = :status,
                        status_reason = :reason,
                        status_changed_at = NOW(),
                        deletion_scheduled_at = NULL
                    WHERE id = :user_id AND role = 'user'
                """),
                {"status": new_status, "reason": reason, "user_id": user_id}
            )

        elif action == "reactivate":
            new_status = "active"
            db.session.execute(
                text("""
                    UPDATE users
                    SET status = 'active',
                        status_reason = :reason,
                        status_changed_at = NOW(),
                        deletion_scheduled_at = NULL
                    WHERE id = :user_id AND role = 'user'
                """),
                {"reason": reason, "user_id": user_id}
            )

        elif action == "schedule_delete":
            new_status = "pending_deletion"
            db.session.execute(
                text("""
                    UPDATE users
                    SET status = 'pending_deletion',
                        status_reason = :reason,
                        status_changed_at = NOW(),
                        deletion_scheduled_at = DATE_ADD(NOW(), INTERVAL 7 DAY)
                    WHERE id = :user_id AND role = 'user'
                """),
                {"reason": reason, "user_id": user_id}
            )

        elif action == "cancel_delete":
            new_status = "active"
            db.session.execute(
                text("""
                    UPDATE users
                    SET status = 'active',
                        status_reason = :reason,
                        status_changed_at = NOW(),
                        deletion_scheduled_at = NULL
                    WHERE id = :user_id AND role = 'user'
                """),
                {"reason": reason, "user_id": user_id}
            )

        db.session.execute(
            text("""
                INSERT INTO user_notifications
                (user_id, notification_type, title, message)
                VALUES (:user_id, :type, :title, :message)
            """),
            {
                "user_id": user_id,
                "type": action,
                "title": titles[action],
                "message": messages[action]
            }
        )

        db.session.execute(
            text("""
                INSERT INTO admin_logs
                (admin_id, admin_email, action, target_type, target_id,
                 target_details, reason, old_value, new_value, ip_address)
                VALUES
                (:admin_id, :admin_email, :action, 'User', :target_id,
                 :target_details, :reason, :old_value, :new_value, :ip_address)
            """),
            {
                "admin_id": admin_id,
                "admin_email": admin_email,
                "action": titles[action],
                "target_id": user_id,
                "target_details": user.email,
                "reason": reason,
                "old_value": old_status,
                "new_value": new_status,
                "ip_address": ip_address
            }
        )

        db.session.commit()

        return {
            "status": new_status,
            "title": titles[action],
            "message": messages[action]
        }

    except Exception:
        db.session.rollback()
        raise


# =====================================================
# GET SINGLE GENERATED CONTENT
# =====================================================

def get_content_by_id(content_id):

    return db.session.execute(
        text("""
            SELECT
                id,
                user_email,
                topic,
                content,
                word_count,
                content_type,
                created_at
            FROM generated_content
            WHERE id = :content_id
        """),
        {
            "content_id": content_id
        }
    ).mappings().first()


# =====================================================
# DELETE GENERATED CONTENT
# =====================================================

def delete_content(content_id):

    result = db.session.execute(
        text("""
            DELETE FROM generated_content
            WHERE id = :content_id
        """),
        {
            "content_id": content_id
        }
    )

    db.session.commit()

    return result.rowcount > 0


# =====================================================
# DELETE USER + ALL RELATED DATA
# =====================================================

def delete_user(user_id):

    # -------------------------------------------------
    # GET USER
    # -------------------------------------------------

    user = User.query.filter_by(
        id=user_id,
        role="user"
    ).first()

    if not user:
        return False


    # -------------------------------------------------
    # SAVE USER INFORMATION
    # -------------------------------------------------

    user_id = user.id
    user_email = user.email


    try:

        # =================================================
        # 1. DELETE SEO REPORTS
        # =================================================

        result = db.session.execute(
            text("""
                DELETE FROM seo_history
                WHERE user_email = :user_email
            """),
            {
                "user_email": user_email
            }
        )

        print("SEO DELETED:", result.rowcount)


        # =================================================
        # 2. DELETE PLAGIARISM HISTORY
        # =================================================

        result = db.session.execute(
            text("""
                DELETE FROM plagiarism_history
                WHERE user_id = :user_id
                   OR user_email = :user_email
            """),
            {
                "user_id": user_id,
                "user_email": user_email
            }
        )

        print("PLAGIARISM DELETED:", result.rowcount)


        # =================================================
        # 3. DELETE HUMANIZED HISTORY
        # =================================================

        result = db.session.execute(
            text("""
                DELETE FROM humanized_history
                WHERE user_id = :user_id
                   OR user_email = :user_email
            """),
            {
                "user_id": user_id,
                "user_email": user_email
            }
        )

        print("HUMANIZED DELETED:", result.rowcount)


        # =================================================
        # 4. DELETE GENERATED CONTENT
        # =================================================

        result = db.session.execute(
            text("""
                DELETE FROM generated_content
                WHERE user_id = :user_id
                   OR user_email = :user_email
            """),
            {
                "user_id": user_id,
                "user_email": user_email
            }
        )

        print("GENERATED CONTENT DELETED:", result.rowcount)


        # =================================================
        # 5. DELETE FEEDBACK
        # =================================================

        result = db.session.execute(
            text("""
                DELETE FROM feedback
                WHERE user_email = :user_email
            """),
            {
                "user_email": user_email
            }
        )

        print("FEEDBACK DELETED:", result.rowcount)


        # =================================================
        # 6. DELETE USER
        # =================================================

        db.session.delete(user)

        print("USER DELETE MARKED:", user_id)


        # =================================================
        # 7. COMMIT EVERYTHING
        # =================================================

        db.session.commit()


        print("========================================")
        print("USER AND ALL RELATED DATA DELETED")
        print("USER ID:", user_id)
        print("USER EMAIL:", user_email)
        print("========================================")


        return True


    except Exception as e:

        # -------------------------------------------------
        # ROLLBACK IF ANYTHING FAILS
        # -------------------------------------------------

        db.session.rollback()

        print("========================================")
        print("DELETE USER + RELATED DATA ERROR:")
        print(e)
        print("========================================")

        raise
    # =====================================================
# ADMIN ACTIVITY LOGS
# =====================================================

def get_admin_logs():

    return db.session.execute(
        text("""
            SELECT
                id,
                admin_id,
                admin_email,
                action,
                target_type,
                target_details,
                created_at
            FROM admin_logs
            ORDER BY created_at DESC
        """)
    ).mappings().all()


# =====================================================
# ADD ADMIN ACTIVITY LOG
# =====================================================

def add_admin_log(
    admin_id,
    admin_email,
    action,
    target_type=None,
    target_details=None
):

    try:

        db.session.execute(
            text("""
                INSERT INTO admin_logs
                (
                    admin_id,
                    admin_email,
                    action,
                    target_type,
                    target_details
                )
                VALUES
                (
                    :admin_id,
                    :admin_email,
                    :action,
                    :target_type,
                    :target_details
                )
            """),
            {
                "admin_id": admin_id,
                "admin_email": admin_email,
                "action": action,
                "target_type": target_type,
                "target_details": target_details
            }
        )

        db.session.commit()

        return True

    except Exception as e:

        db.session.rollback()

        print(
            "ADD ADMIN LOG ERROR:",
            e
        )

        return False
    # =====================================================
# ADMIN SETTINGS
# =====================================================

# =====================================================
# ADMIN SETTINGS
# =====================================================

def get_admin_settings():

    return db.session.execute(
        text("""
            SELECT
                id,
                site_name,
                plagiarism_threshold,
                seo_target_score,
                default_word_limit,
                updated_at
            FROM admin_settings
            ORDER BY id ASC
            LIMIT 1
        """)
    ).mappings().first()


# =====================================================
# UPDATE ADMIN SETTINGS
# =====================================================

def update_admin_settings(data):

    try:

        settings = get_admin_settings()

        if settings:

            db.session.execute(
                text("""
                    UPDATE admin_settings
                    SET
                        site_name = :site_name,
                        plagiarism_threshold = :plagiarism_threshold,
                        seo_target_score = :seo_target_score,
                        default_word_limit = :default_word_limit
                    WHERE id = :id
                """),
                {
                    "id": settings["id"],
                    "site_name": data["site_name"],
                    "plagiarism_threshold":
                        data["plagiarism_threshold"],
                    "seo_target_score":
                        data["seo_target_score"],
                    "default_word_limit":
                        data["default_word_limit"]
                }
            )

        else:

            db.session.execute(
                text("""
                    INSERT INTO admin_settings
                    (
                        site_name,
                        plagiarism_threshold,
                        seo_target_score,
                        default_word_limit
                    )
                    VALUES
                    (
                        :site_name,
                        :plagiarism_threshold,
                        :seo_target_score,
                        :default_word_limit
                    )
                """),
                {
                    "site_name": data["site_name"],
                    "plagiarism_threshold":
                        data["plagiarism_threshold"],
                    "seo_target_score":
                        data["seo_target_score"],
                    "default_word_limit":
                        data["default_word_limit"]
                }
            )

        db.session.commit()

        return True

    except Exception as e:

        db.session.rollback()

        print(
            "UPDATE ADMIN SETTINGS ERROR:",
            e
        )

        raise

