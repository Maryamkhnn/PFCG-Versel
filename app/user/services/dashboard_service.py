from sqlalchemy import text
from app.database import db
# DASHBOARD SERVICE

def get_dashboard_data(user_email):

    # GENERATED CONTENT COUNT

    generated_count = db.session.execute(
        text("""
            SELECT COUNT(*)
            FROM generated_content
            WHERE LOWER(TRIM(user_email))
                = LOWER(TRIM(:email))
        """),
        {
            "email": user_email
        }
    ).scalar() or 0


    # HUMANIZED CONTENT COUNT

    humanized_count = db.session.execute(
        text("""
            SELECT COUNT(*)
            FROM humanized_history
            WHERE LOWER(TRIM(user_email))
                = LOWER(TRIM(:email))
        """),
        {
            "email": user_email
        }
    ).scalar() or 0


    # TOTAL WORDS

    total_words = db.session.execute(
        text("""
            SELECT COALESCE(
                SUM(COALESCE(word_count, 0)),
                0
            )
            FROM generated_content
            WHERE LOWER(TRIM(user_email))
                = LOWER(TRIM(:email))
        """),
        {
            "email": user_email
        }
    ).scalar() or 0


    # PLAGIARISM REPORT COUNT

    reports_count = db.session.execute(
        text("""
            SELECT COUNT(*)
            FROM plagiarism_history
            WHERE LOWER(TRIM(user_email))
                = LOWER(TRIM(:email))
        """),
        {
            "email": user_email
        }
    ).scalar() or 0

    # SAVED DOCUMENT COUNT


    saved_documents = db.session.execute(
        text("""
            SELECT COUNT(*)
            FROM saved_documents
            WHERE LOWER(TRIM(user_email))
                = LOWER(TRIM(:email))
        """),
        {
            "email": user_email
        }
    ).scalar() or 0

       # =====================================================
    # RECENT ACTIVITIES
    # Maximum 5 latest records from each activity type
    # =====================================================

    recent_activities = db.session.execute(
        text("""
            SELECT
                activity_id,
                activity_type,
                title,
                word_count,
                created_at

            FROM
            (

                /* =========================================
                   LATEST 5 AI GENERATED CONTENT
                ========================================= */

                SELECT *
                FROM (
                    SELECT
                        id AS activity_id,

                        'generated' AS activity_type,

                        COALESCE(
                            NULLIF(TRIM(topic), ''),
                            'Generated Content'
                        ) AS title,

                        COALESCE(
                            word_count,
                            0
                        ) AS word_count,

                        created_at

                    FROM generated_content

                    WHERE LOWER(TRIM(user_email))
                        = LOWER(TRIM(:email))

                    ORDER BY
                        created_at DESC,
                        id DESC

                    LIMIT 5
                ) AS generated_recent


                UNION ALL


                /* =========================================
                   LATEST 5 HUMANIZED CONTENT
                ========================================= */

                SELECT *
                FROM (
                    SELECT
                        id AS activity_id,

                        'humanized' AS activity_type,

                        'Content Humanized' AS title,

                        COALESCE(
                            word_count,
                            0
                        ) AS word_count,

                        created_at

                    FROM humanized_history

                    WHERE LOWER(TRIM(user_email))
                        = LOWER(TRIM(:email))

                    ORDER BY
                        created_at DESC,
                        id DESC

                    LIMIT 5
                ) AS humanized_recent


                UNION ALL


                /* =========================================
                   LATEST 5 PLAGIARISM REPORTS
                ========================================= */

                SELECT *
                FROM (
                    SELECT
                        id AS activity_id,

                        'plagiarism' AS activity_type,

                        COALESCE(
                            NULLIF(TRIM(topic), ''),
                            'Plagiarism Check'
                        ) AS title,

                        COALESCE(
                            word_count,
                            0
                        ) AS word_count,

                        created_at

                    FROM plagiarism_history

                    WHERE LOWER(TRIM(user_email))
                        = LOWER(TRIM(:email))

                    ORDER BY
                        created_at DESC,
                        id DESC

                    LIMIT 5
                ) AS plagiarism_recent


                UNION ALL


                /* =========================================
                   LATEST 5 SEO REPORTS
                ========================================= */

                SELECT *
                FROM (
                    SELECT
                        id AS activity_id,

                        'seo' AS activity_type,

                        COALESCE(
                            NULLIF(
                                TRIM(content_topic),
                                ''
                            ),
                            'SEO Analysis'
                        ) AS title,

                        COALESCE(
                            word_count,
                            0
                        ) AS word_count,

                        created_at

                    FROM seo_history

                    WHERE LOWER(TRIM(user_email))
                        = LOWER(TRIM(:email))

                    ORDER BY
                        created_at DESC,
                        id DESC

                    LIMIT 5
                ) AS seo_recent

            ) AS activities

            ORDER BY
                created_at DESC,
                activity_id DESC

        """),
        {
            "email": user_email
        }
    ).mappings().all()
    top_topics = db.session.execute(
        text("""
            SELECT
                topic,
                COUNT(*) AS total

            FROM generated_content

            WHERE LOWER(TRIM(user_email))
                = LOWER(TRIM(:email))

              AND topic IS NOT NULL

              AND TRIM(topic) <> ''

            GROUP BY topic

            ORDER BY
                total DESC,
                topic ASC

            LIMIT 5
        """),
        {
            "email": user_email
        }
    ).fetchall()


    # RETURN DATA
    
    return {
        "generated_count": generated_count,
        "humanized_count": humanized_count,
        "total_words": total_words,
        "reports_count": reports_count,
        "saved_documents": saved_documents,
        "recent_activities": recent_activities,
        "top_topics": top_topics
    }