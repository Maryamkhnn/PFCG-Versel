from sqlalchemy import text

from app.database import db


# ============================================================
# DATE FORMATTER
# ============================================================

def format_date(value):

    if not value:
        return "--"

    try:
        return value.strftime("%Y-%m-%d %H:%M")

    except Exception:
        return str(value)


# ============================================================
# GET ALL USER REPORTS
# ============================================================

def get_user_reports(user_email):

    if not user_email:
        return []

    reports = []

    try:

        # ====================================================
        # 1. PLAGIARISM REPORTS
        # ====================================================

        result = db.session.execute(
            text("""
                SELECT
                    id,
                    user_email,
                    score,
                    created_at,
                    topic,
                    content,
                    matched_sources
                FROM plagiarism_reports
                WHERE user_email = :email
                ORDER BY id DESC
            """),
            {
                "email": user_email
            }
        )

        rows = result.mappings().all()

        for row in rows:

            score = row["score"] or 0

            if score <= 15:
                status = "Excellent"

            elif score <= 30:
                status = "Good"

            elif score <= 50:
                status = "Warning"

            else:
                status = "High Plagiarism"

            reports.append({

                "id": row["id"],

                "topic": (
                    row["topic"]
                    or "Untitled Content"
                ),

                "type": "Plagiarism",

                "score": score,

                "score_label": f"{score}%",

                "status": status,

                "date": format_date(
                    row["created_at"]
                ),

                "content": (
                    row["content"]
                    or ""
                ),

                "matched_sources": (
                    row["matched_sources"]
                    or ""
                )

            })


        # ====================================================
        # 2. HUMANIZER REPORTS
        # ====================================================

        result = db.session.execute(
            text("""
                SELECT
                    id,
                    user_email,
                    original_content,
                    humanized_content,
                    word_count,
                    created_at
                FROM humanized_history
                WHERE user_email = :email
                ORDER BY id DESC
            """),
            {
                "email": user_email
            }
        )

        rows = result.mappings().all()

        for row in rows:

            reports.append({

                "id": row["id"],

                "topic": "Humanized Content",

                "type": "Humanizer",

                "score": None,

                "score_label": "Completed",

                "status": "Humanized",

                "date": format_date(
                    row["created_at"]
                ),

                "content": (
                    row["humanized_content"]
                    or ""
                ),

                "original_content": (
                    row["original_content"]
                    or ""
                ),

                "word_count": (
                    row["word_count"]
                    or 0
                ),

                "matched_sources": ""

            })


        # ====================================================
        # 3. SEO REPORTS
        # ====================================================

        result = db.session.execute(
            text("""
                SELECT
                    id,
                    content_topic,
                    word_count,
                    seo_score,
                    readability_score,
                    keyword_density,
                    keyword_count,
                    seo_status,
                    created_at,
                    user_email,
                    content_id
                FROM seo_history
                WHERE user_email = :email
                ORDER BY id DESC
            """),
            {
                "email": user_email
            }
        )

        rows = result.mappings().all()

        for row in rows:

            score = row["seo_score"] or 0

            reports.append({

                "id": row["id"],

                "topic": (
                    row["content_topic"]
                    or "Untitled Content"
                ),

                "type": "SEO",

                "score": score,

                "score_label": f"{score}%",

                "status": (
                    row["seo_status"]
                    or "Analyzed"
                ),

                "date": format_date(
                    row["created_at"]
                ),

                "content": "",

                "matched_sources": "",

                "word_count": (
                    row["word_count"]
                    or 0
                ),

                "readability_score": (
                    row["readability_score"]
                    or 0
                ),

                "keyword_density": (
                    row["keyword_density"]
                    or 0
                ),

                "keyword_count": (
                    row["keyword_count"]
                    or 0
                ),

                "content_id": (
                    row["content_id"]
                )

            })


        # ====================================================
        # 4. GENERATED CONTENT
        # ====================================================

        result = db.session.execute(
            text("""
                SELECT
                    id,
                    user_email,
                    topic,
                    content,
                    content_type,
                    word_count,
                    created_at
                FROM generated_content
                WHERE user_email = :email
                ORDER BY id DESC
            """),
            {
                "email": user_email
            }
        )

        rows = result.mappings().all()

        for row in rows:

            reports.append({

                "id": row["id"],

                "topic": (
                    row["topic"]
                    or "Untitled Content"
                ),

                "type": "Generated Content",

                "score": None,

                "score_label": "Generated",

                "status": "Completed",

                "date": format_date(
                    row["created_at"]
                ),

                "content": (
                    row["content"]
                    or ""
                ),

                "content_type": (
                    row["content_type"]
                    or "Content"
                ),

                "word_count": (
                    row["word_count"]
                    or 0
                ),

                "matched_sources": ""

            })


        # ====================================================
        # SORT ALL REPORTS BY DATE
        # ====================================================

        reports.sort(
            key=lambda x: x["date"],
            reverse=True
        )

        return reports


    except Exception as e:

        print(
            "GET USER REPORTS ERROR:",
            e
        )

        raise


# ============================================================
# GET SINGLE REPORT
# ============================================================

def get_report_by_id(
    user_email,
    report_type,
    report_id
):

    if not user_email or not report_id:
        return None

    try:

        # ====================================================
        # PLAGIARISM
        # ====================================================

        if report_type == "Plagiarism":

            result = db.session.execute(
                text("""
                    SELECT
                        id,
                        topic,
                        content,
                        score,
                        matched_sources,
                        created_at
                    FROM plagiarism_reports
                    WHERE id = :id
                    AND user_email = :email
                    LIMIT 1
                """),
                {
                    "id": report_id,
                    "email": user_email
                }
            )

            row = result.mappings().first()

            if not row:
                return None

            return {

                "id": row["id"],

                "topic": (
                    row["topic"]
                    or "Untitled Content"
                ),

                "type": "Plagiarism",

                "score": (
                    row["score"]
                    or 0
                ),

                "content": (
                    row["content"]
                    or ""
                ),

                "matched_sources": (
                    row["matched_sources"]
                    or ""
                ),

                "status": "Completed",

                "date": format_date(
                    row["created_at"]
                )

            }


        # ====================================================
        # HUMANIZER
        # ====================================================

        if report_type == "Humanizer":

            result = db.session.execute(
                text("""
                    SELECT
                        id,
                        original_content,
                        humanized_content,
                        word_count,
                        created_at
                    FROM humanized_history
                    WHERE id = :id
                    AND user_email = :email
                    LIMIT 1
                """),
                {
                    "id": report_id,
                    "email": user_email
                }
            )

            row = result.mappings().first()

            if not row:
                return None

            return {

                "id": row["id"],

                "topic": "Humanized Content",

                "type": "Humanizer",

                "score": None,

                "original_content": (
                    row["original_content"]
                    or ""
                ),

                "humanized_content": (
                    row["humanized_content"]
                    or ""
                ),

                "word_count": (
                    row["word_count"]
                    or 0
                ),

                "status": "Humanized",

                "date": format_date(
                    row["created_at"]
                )

            }


        # ====================================================
        # SEO
        # ====================================================

        if report_type == "SEO":

            result = db.session.execute(
                text("""
                    SELECT
                        id,
                        content_topic,
                        word_count,
                        seo_score,
                        readability_score,
                        keyword_density,
                        keyword_count,
                        seo_status,
                        created_at,
                        content_id
                    FROM seo_history
                    WHERE id = :id
                    AND user_email = :email
                    LIMIT 1
                """),
                {
                    "id": report_id,
                    "email": user_email
                }
            )

            row = result.mappings().first()

            if not row:
                return None

            return {

                "id": row["id"],

                "topic": (
                    row["content_topic"]
                    or "Untitled Content"
                ),

                "type": "SEO",

                "score": (
                    row["seo_score"]
                    or 0
                ),

                "word_count": (
                    row["word_count"]
                    or 0
                ),

                "readability_score": (
                    row["readability_score"]
                    or 0
                ),

                "keyword_density": (
                    row["keyword_density"]
                    or 0
                ),

                "keyword_count": (
                    row["keyword_count"]
                    or 0
                ),

                "status": (
                    row["seo_status"]
                    or "Analyzed"
                ),

                "content_id": (
                    row["content_id"]
                ),

                "date": format_date(
                    row["created_at"]
                )

            }


        # ====================================================
        # GENERATED CONTENT
        # ====================================================

        if report_type == "Generated Content":

            result = db.session.execute(
                text("""
                    SELECT
                        id,
                        topic,
                        content,
                        content_type,
                        word_count,
                        created_at
                    FROM generated_content
                    WHERE id = :id
                    AND user_email = :email
                    LIMIT 1
                """),
                {
                    "id": report_id,
                    "email": user_email
                }
            )

            row = result.mappings().first()

            if not row:
                return None

            return {

                "id": row["id"],

                "topic": (
                    row["topic"]
                    or "Untitled Content"
                ),

                "type": "Generated Content",

                "score": None,

                "content": (
                    row["content"]
                    or ""
                ),

                "content_type": (
                    row["content_type"]
                    or "Content"
                ),

                "word_count": (
                    row["word_count"]
                    or 0
                ),

                "status": "Completed",

                "date": format_date(
                    row["created_at"]
                )

            }


        return None


    except Exception as e:

        print(
            "GET SINGLE REPORT ERROR:",
            e
        )

        raise


# ============================================================
# DELETE REPORT
# ============================================================

def delete_report(
    user_email,
    report_type,
    report_id
):

    if not user_email or not report_id:
        return False


    table_map = {

        "Plagiarism":
            "plagiarism_reports",

        "Humanizer":
            "humanized_history",

        "SEO":
            "seo_history",

        "Generated Content":
            "generated_content"

    }


    table_name = table_map.get(
        report_type
    )


    if not table_name:
        return False


    try:

        result = db.session.execute(
            text(f"""
                DELETE FROM {table_name}
                WHERE id = :id
                AND user_email = :email
            """),
            {
                "id": report_id,
                "email": user_email
            }
        )


        if result.rowcount == 0:

            db.session.rollback()

            return False


        db.session.commit()

        return True


    except Exception as e:

        db.session.rollback()

        print(
            "DELETE REPORT ERROR:",
            e
        )

        raise