from flask import render_template, jsonify, session
from sqlalchemy import text
from app.database import db
import traceback
import json


# =========================================================
# HELPER: DATETIME
# =========================================================

def format_datetime(value):
    if not value:
        return ""

    try:
        return value.strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return str(value)


# =========================================================
# HELPER: SOURCES
# =========================================================

def parse_sources(value):

    if not value:
        return []

    if isinstance(value, list):
        return value

    try:
        return json.loads(value)
    except Exception:
        return []


# =========================================================
# REPORTS PAGE
# =========================================================

def reports_page():

    try:

        print("\n====================================")
        print("          REPORTS PAGE")
        print("====================================")

        user_id = session.get("user_id")

        print("USER ID:", user_id)
        print("USER EMAIL:", session.get("user_email"))

        if not user_id:
            return "User session not found.", 401

        # =================================================
        # GET GENERATED CONTENT + LATEST REPORTS
        # =================================================

        reports = db.session.execute(
            text("""
                SELECT

                    gc.id,
                    gc.topic,
                    gc.content,
                    gc.word_count,
                    gc.content_type,
                    gc.created_at,

                    /* =========================
                       AI PLAGIARISM
                       ========================= */

                    (
                        SELECT ph.score
                        FROM plagiarism_history ph
                        WHERE ph.user_id = gc.user_id
                        AND ph.topic = gc.topic
                        AND ph.check_type = 'AI'
                        ORDER BY ph.id DESC
                        LIMIT 1
                    ) AS ai_plagiarism_score,


                    /* =========================
                       HUMANIZED PLAGIARISM
                       ========================= */

                    (
                        SELECT ph.score
                        FROM plagiarism_history ph
                        WHERE ph.user_id = gc.user_id
                        AND ph.topic = gc.topic
                        AND ph.check_type = 'HUMANIZED'
                        ORDER BY ph.id DESC
                        LIMIT 1
                    ) AS humanized_plagiarism_score,


                    /* =========================
                       AI SOURCES
                       ========================= */

                    (
                        SELECT ph.matched_sources
                        FROM plagiarism_history ph
                        WHERE ph.user_id = gc.user_id
                        AND ph.topic = gc.topic
                        AND ph.check_type = 'AI'
                        ORDER BY ph.id DESC
                        LIMIT 1
                    ) AS ai_matched_sources,


                    /* =========================
                       HUMANIZED SOURCES
                       ========================= */

                    (
                        SELECT ph.matched_sources
                        FROM plagiarism_history ph
                        WHERE ph.user_id = gc.user_id
                        AND ph.topic = gc.topic
                        AND ph.check_type = 'HUMANIZED'
                        ORDER BY ph.id DESC
                        LIMIT 1
                    ) AS humanized_matched_sources,


                    /* =========================
                       HUMANIZED CONTENT
                       ========================= */

                    (
                        SELECT hh.id
                        FROM humanized_history hh
                        WHERE hh.user_id = gc.user_id
                        AND hh.original_content = gc.content
                        ORDER BY hh.id DESC
                        LIMIT 1
                    ) AS humanized_id,


                    /* =========================
                       SEO SCORE
                       ========================= */

                    (
                        SELECT sh.seo_score
                        FROM seo_history sh
                        WHERE LOWER(TRIM(sh.user_email))
                            = LOWER(TRIM(gc.user_email))
                          AND (
                            (sh.source_type = 'ai'
                             AND sh.source_id = gc.id)
                            OR
                            (sh.source_type = 'humanized'
                             AND sh.source_id = (
                                SELECT hh2.id
                                FROM humanized_history hh2
                                WHERE hh2.user_id = gc.user_id
                                  AND CAST(hh2.original_content AS BINARY)
                                    = CAST(gc.content AS BINARY)
                                ORDER BY hh2.id DESC
                                LIMIT 1
                             ))
                            OR
                            (sh.content_id = gc.id
                             AND (sh.source_type = 'ai'
                                  OR sh.source_type IS NULL))
                          )
                        ORDER BY sh.id DESC
                        LIMIT 1
                    ) AS seo_score,

                    (
                        SELECT sh.source_type
                        FROM seo_history sh
                        WHERE LOWER(TRIM(sh.user_email))
                            = LOWER(TRIM(gc.user_email))
                          AND (
                            (sh.source_type = 'ai' AND sh.source_id = gc.id)
                            OR (sh.source_type = 'humanized' AND sh.source_id = (
                                SELECT hh2.id FROM humanized_history hh2
                                WHERE hh2.user_id = gc.user_id
                                  AND CAST(hh2.original_content AS BINARY)
                                    = CAST(gc.content AS BINARY)
                                ORDER BY hh2.id DESC LIMIT 1
                            ))
                            OR (sh.content_id = gc.id AND
                                (sh.source_type = 'ai' OR sh.source_type IS NULL))
                          )
                        ORDER BY sh.id DESC
                        LIMIT 1
                    ) AS seo_source_type,

                    /* =========================
                       KEYWORD DENSITY
                       ========================= */

                    (
                        SELECT sh.keyword_density
                        FROM seo_history sh
                        WHERE LOWER(TRIM(sh.user_email))
                            = LOWER(TRIM(gc.user_email))
                          AND (
                            (sh.source_type = 'ai' AND sh.source_id = gc.id)
                            OR (sh.source_type = 'humanized' AND sh.source_id = (
                                SELECT hh2.id FROM humanized_history hh2
                                WHERE hh2.user_id = gc.user_id
                                  AND CAST(hh2.original_content AS BINARY)
                                    = CAST(gc.content AS BINARY)
                                ORDER BY hh2.id DESC LIMIT 1
                            ))
                            OR (sh.content_id = gc.id AND
                                (sh.source_type = 'ai' OR sh.source_type IS NULL))
                          )
                        ORDER BY sh.id DESC
                        LIMIT 1
                    ) AS keyword_density,


                    /* =========================
                       KEYWORD COUNT
                       ========================= */

                    (
                        SELECT sh.keyword_count
                        FROM seo_history sh
                        WHERE LOWER(TRIM(sh.user_email))
                            = LOWER(TRIM(gc.user_email))
                          AND (
                            (sh.source_type = 'ai' AND sh.source_id = gc.id)
                            OR (sh.source_type = 'humanized' AND sh.source_id = (
                                SELECT hh2.id FROM humanized_history hh2
                                WHERE hh2.user_id = gc.user_id
                                  AND CAST(hh2.original_content AS BINARY)
                                    = CAST(gc.content AS BINARY)
                                ORDER BY hh2.id DESC LIMIT 1
                            ))
                            OR (sh.content_id = gc.id AND
                                (sh.source_type = 'ai' OR sh.source_type IS NULL))
                          )
                        ORDER BY sh.id DESC
                        LIMIT 1
                    ) AS keyword_count,


                    /* =========================
                       SEO STATUS
                       ========================= */

                    (
                        SELECT sh.seo_status
                        FROM seo_history sh
                        WHERE LOWER(TRIM(sh.user_email))
                            = LOWER(TRIM(gc.user_email))
                          AND (
                            (sh.source_type = 'ai' AND sh.source_id = gc.id)
                            OR (sh.source_type = 'humanized' AND sh.source_id = (
                                SELECT hh2.id FROM humanized_history hh2
                                WHERE hh2.user_id = gc.user_id
                                  AND CAST(hh2.original_content AS BINARY)
                                    = CAST(gc.content AS BINARY)
                                ORDER BY hh2.id DESC LIMIT 1
                            ))
                            OR (sh.content_id = gc.id AND
                                (sh.source_type = 'ai' OR sh.source_type IS NULL))
                          )
                        ORDER BY sh.id DESC
                        LIMIT 1
                    ) AS seo_status

                FROM generated_content gc

WHERE gc.user_id = :user_id

AND (
    /* Plagiarism report exists */
    EXISTS (
        SELECT 1
        FROM plagiarism_history ph
        WHERE ph.user_id = gc.user_id
          AND ph.topic = gc.topic
    )

    OR

    /* SEO report exists */
    EXISTS (
        SELECT 1
        FROM seo_history sh
        WHERE LOWER(TRIM(sh.user_email))
            = LOWER(TRIM(gc.user_email))

          AND (
                (
                    sh.source_type = 'ai'
                    AND sh.source_id = gc.id
                )

                OR

                (
                    sh.content_id = gc.id
                    AND (
                        sh.source_type = 'ai'
                        OR sh.source_type IS NULL
                    )
                )

                OR

                (
                    sh.source_type = 'humanized'
                    AND sh.source_id = (
                        SELECT hh2.id
                        FROM humanized_history hh2
                        WHERE hh2.user_id = gc.user_id
                          AND CAST(hh2.original_content AS BINARY)
                              = CAST(gc.content AS BINARY)
                        ORDER BY hh2.id DESC
                        LIMIT 1
                    )
                )
          )
    )
)

ORDER BY gc.id DESC
            """),
            {
                "user_id": user_id
            }
        ).mappings().all()


        # =================================================
        # CONVERT DATABASE ROWS
        # =================================================

        final_reports = []

        for report in reports:

            ai_sources = parse_sources(
                report["ai_matched_sources"]
            )

            humanized_sources = parse_sources(
                report["humanized_matched_sources"]
            )

            final_reports.append({

                "id": report["id"],

                "topic": (
                    report["topic"]
                    or "Untitled Content"
                ),
                    "content": (
        report["content"]
        or ""
    ),

              "type": "SEO",
                "word_count": (
                    report["word_count"]
                    or 0
                ),

                "content_type": (
                    report["content_type"]
                    or "Content"
                ),

                "created_at": format_datetime(
                    report["created_at"]
                ),

                "ai_plagiarism_score": (
                    float(report["ai_plagiarism_score"])
                    if report["ai_plagiarism_score"] is not None
                    else None
                ),

                "humanized_plagiarism_score": (
                    float(report["humanized_plagiarism_score"])
                    if report["humanized_plagiarism_score"] is not None
                    else None
                ),

                "ai_matched_sources": ai_sources,

                "humanized_matched_sources": humanized_sources,

                "ai_source_count": len(ai_sources),

                "humanized_source_count": len(
                    humanized_sources
                ),

                "humanized_id": report["humanized_id"],

                "seo_score": (
                    float(report["seo_score"])
                    if report["seo_score"] is not None
                    else None
                ),

                "seo_source_type": (
                    report["seo_source_type"] or "ai"
                ),


                "keyword_density": (
                    float(report["keyword_density"])
                    if report["keyword_density"] is not None
                    else None
                ),

                "keyword_count": (
                    int(report["keyword_count"])
                    if report["keyword_count"] is not None
                    else None
                ),

                "seo_status": (
                    report["seo_status"]
                    or "Not Checked"
                )
            })


        print(
            "REPORTS FOUND:",
            len(final_reports)
        )

        print("====================================\n")


        # =================================================
        # PAGE
        # =================================================

        return render_template(
            "user/reports.html",
            reports=final_reports
        )


    except Exception as e:

        print("\n====================================")
        print("       REPORTS PAGE ERROR")
        print("====================================")

        traceback.print_exc()

        db.session.rollback()

        return "Unable to load reports.", 500


# =========================================================
# GET ALL REPORTS API
# =========================================================

def get_reports_api():

    try:

        user_id = session.get("user_id")

        if not user_id:

            return jsonify({
                "success": False,
                "message": "User session not found.",
                "reports": []
            }), 401


        reports = db.session.execute(
            text("""
                SELECT

                    gc.id,
                    gc.topic,
                    gc.content,
                    gc.word_count,
                    gc.content_type,
                    gc.created_at,

                    (
                        SELECT ph.score
                        FROM plagiarism_history ph
                        WHERE ph.user_id = gc.user_id
                        AND ph.topic = gc.topic
                        AND ph.check_type = 'AI'
                        ORDER BY ph.id DESC
                        LIMIT 1
                    ) AS ai_score,

                    (
                        SELECT ph.score
                        FROM plagiarism_history ph
                        WHERE ph.user_id = gc.user_id
                        AND ph.topic = gc.topic
                        AND ph.check_type = 'HUMANIZED'
                        ORDER BY ph.id DESC
                        LIMIT 1
                    ) AS humanized_score,

                    (
                        SELECT ph.matched_sources
                        FROM plagiarism_history ph
                        WHERE ph.user_id = gc.user_id
                        AND ph.topic = gc.topic
                        AND ph.check_type = 'AI'
                        ORDER BY ph.id DESC
                        LIMIT 1
                    ) AS ai_sources,

                    (
                        SELECT ph.matched_sources
                        FROM plagiarism_history ph
                        WHERE ph.user_id = gc.user_id
                        AND ph.topic = gc.topic
                        AND ph.check_type = 'HUMANIZED'
                        ORDER BY ph.id DESC
                        LIMIT 1
                    ) AS humanized_sources,

                    (
                        SELECT sh.seo_score
                        FROM seo_history sh
                        WHERE LOWER(TRIM(sh.user_email)) = LOWER(TRIM(gc.user_email))
                          AND (
                            (sh.source_type = 'ai' AND sh.source_id = gc.id)
                            OR (sh.source_type = 'humanized' AND sh.source_id = (
                                SELECT hh2.id FROM humanized_history hh2
                                WHERE hh2.user_id = gc.user_id
                                  AND CAST(hh2.original_content AS BINARY)
                                    = CAST(gc.content AS BINARY)
                                ORDER BY hh2.id DESC LIMIT 1
                            ))
                            OR (sh.content_id = gc.id AND
                                (sh.source_type = 'ai' OR sh.source_type IS NULL))
                          )
                        ORDER BY sh.id DESC
                        LIMIT 1
                    ) AS seo_score,

                    (
                        SELECT sh.source_type
                        FROM seo_history sh
                        WHERE LOWER(TRIM(sh.user_email)) = LOWER(TRIM(gc.user_email))
                          AND (
                            (sh.source_type = 'ai' AND sh.source_id = gc.id)
                            OR (sh.source_type = 'humanized' AND sh.source_id = (
                                SELECT hh2.id FROM humanized_history hh2
                                WHERE hh2.user_id = gc.user_id
                                  AND CAST(hh2.original_content AS BINARY)
                                    = CAST(gc.content AS BINARY)
                                ORDER BY hh2.id DESC LIMIT 1
                            ))
                            OR (sh.content_id = gc.id AND
                                (sh.source_type = 'ai' OR sh.source_type IS NULL))
                          )
                        ORDER BY sh.id DESC
                        LIMIT 1
                    ) AS seo_source_type,

                    (
                        SELECT sh.readability_score
                        FROM seo_history sh
                        WHERE LOWER(TRIM(sh.user_email)) = LOWER(TRIM(gc.user_email))
                          AND (
                            (sh.source_type = 'ai' AND sh.source_id = gc.id)
                            OR (sh.source_type = 'humanized' AND sh.source_id = (
                                SELECT hh2.id FROM humanized_history hh2
                                WHERE hh2.user_id = gc.user_id
                                  AND CAST(hh2.original_content AS BINARY)
                                    = CAST(gc.content AS BINARY)
                                ORDER BY hh2.id DESC LIMIT 1
                            ))
                            OR (sh.content_id = gc.id AND
                                (sh.source_type = 'ai' OR sh.source_type IS NULL))
                          )
                        ORDER BY sh.id DESC
                        LIMIT 1
                    ) AS readability_score,

                    (
                        SELECT sh.keyword_density
                        FROM seo_history sh
                        WHERE LOWER(TRIM(sh.user_email)) = LOWER(TRIM(gc.user_email))
                          AND (
                            (sh.source_type = 'ai' AND sh.source_id = gc.id)
                            OR (sh.source_type = 'humanized' AND sh.source_id = (
                                SELECT hh2.id FROM humanized_history hh2
                                WHERE hh2.user_id = gc.user_id
                                  AND CAST(hh2.original_content AS BINARY)
                                    = CAST(gc.content AS BINARY)
                                ORDER BY hh2.id DESC LIMIT 1
                            ))
                            OR (sh.content_id = gc.id AND
                                (sh.source_type = 'ai' OR sh.source_type IS NULL))
                          )
                        ORDER BY sh.id DESC
                        LIMIT 1
                    ) AS keyword_density,

                    (
                        SELECT sh.keyword_count
                        FROM seo_history sh
                        WHERE LOWER(TRIM(sh.user_email)) = LOWER(TRIM(gc.user_email))
                          AND (
                            (sh.source_type = 'ai' AND sh.source_id = gc.id)
                            OR (sh.source_type = 'humanized' AND sh.source_id = (
                                SELECT hh2.id FROM humanized_history hh2
                                WHERE hh2.user_id = gc.user_id
                                  AND CAST(hh2.original_content AS BINARY)
                                    = CAST(gc.content AS BINARY)
                                ORDER BY hh2.id DESC LIMIT 1
                            ))
                            OR (sh.content_id = gc.id AND
                                (sh.source_type = 'ai' OR sh.source_type IS NULL))
                          )
                        ORDER BY sh.id DESC
                        LIMIT 1
                    ) AS keyword_count,

                    (
                        SELECT sh.seo_status
                        FROM seo_history sh
                        WHERE LOWER(TRIM(sh.user_email)) = LOWER(TRIM(gc.user_email))
                          AND (
                            (sh.source_type = 'ai' AND sh.source_id = gc.id)
                            OR (sh.source_type = 'humanized' AND sh.source_id = (
                                SELECT hh2.id FROM humanized_history hh2
                                WHERE hh2.user_id = gc.user_id
                                  AND CAST(hh2.original_content AS BINARY)
                                    = CAST(gc.content AS BINARY)
                                ORDER BY hh2.id DESC LIMIT 1
                            ))
                            OR (sh.content_id = gc.id AND
                                (sh.source_type = 'ai' OR sh.source_type IS NULL))
                          )
                        ORDER BY sh.id DESC
                        LIMIT 1
                    ) AS seo_status

                FROM generated_content gc

WHERE gc.user_id = :user_id

AND (
    /* Plagiarism report exists */
    EXISTS (
        SELECT 1
        FROM plagiarism_history ph
        WHERE ph.user_id = gc.user_id
          AND ph.topic = gc.topic
    )

    OR

    /* SEO report exists */
    EXISTS (
        SELECT 1
        FROM seo_history sh
        WHERE LOWER(TRIM(sh.user_email))
            = LOWER(TRIM(gc.user_email))

          AND (
                (
                    sh.source_type = 'ai'
                    AND sh.source_id = gc.id
                )

                OR

                (
                    sh.content_id = gc.id
                    AND (
                        sh.source_type = 'ai'
                        OR sh.source_type IS NULL
                    )
                )

                OR

                (
                    sh.source_type = 'humanized'
                    AND sh.source_id = (
                        SELECT hh2.id
                        FROM humanized_history hh2
                        WHERE hh2.user_id = gc.user_id
                          AND CAST(hh2.original_content AS BINARY)
                              = CAST(gc.content AS BINARY)
                        ORDER BY hh2.id DESC
                        LIMIT 1
                    )
                )
          )
    )
)

ORDER BY gc.id DESC

                WHERE gc.user_id = :user_id

                ORDER BY gc.id DESC
            """),
            {
                "user_id": user_id
            }
        ).mappings().all()


        final_reports = []


        for report in reports:

            ai_sources = parse_sources(
                report["ai_sources"]
            )

            humanized_sources = parse_sources(
                report["humanized_sources"]
            )


            final_reports.append({

                "id": report["id"],

                "topic": (
                    report["topic"]
                    or "Untitled Content"
                ),

                "content": (
                 report["content"]
                 or ""
                 ),
                "word_count": (
                    report["word_count"]
                    or 0
                ),

                "content_type": (
                    report["content_type"]
                    or "Content"
                ),

                "created_at": format_datetime(
                    report["created_at"]
                ),

                "ai_score": (
                    float(report["ai_score"])
                    if report["ai_score"] is not None
                    else None
                ),

                "humanized_score": (
                    float(report["humanized_score"])
                    if report["humanized_score"] is not None
                    else None
                ),

                "ai_sources": ai_sources,

                "humanized_sources": humanized_sources,

                "ai_source_count": len(ai_sources),

                "humanized_source_count": len(
                    humanized_sources
                ),

                "seo_score": (
                    float(report["seo_score"])
                    if report["seo_score"] is not None
                    else None
                ),

                "seo_source_type": (
                    report["seo_source_type"] or "ai"
                ),

                "keyword_density": (
                    float(report["keyword_density"])
                    if report["keyword_density"] is not None
                    else None
                ),

                "keyword_count": (
                    int(report["keyword_count"])
                    if report["keyword_count"] is not None
                    else None
                ),

                "seo_status": (
                    report["seo_status"]
                    or "Not Checked"
                )
            })


        return jsonify({

            "success": True,

            "reports": final_reports

        })


    except Exception as e:

        print("\n========== GET REPORTS ERROR ==========")

        traceback.print_exc()

        return jsonify({

            "success": False,

            "message": str(e),

            "reports": []

        }), 500


# =========================================================
# GET SINGLE REPORT
# =========================================================

def get_single_report_api(report_id):

    try:

        user_id = session.get("user_id")

        if not user_id:

            return jsonify({
                "success": False,
                "message": "User session not found."
            }), 401


        report = db.session.execute(
            text("""
                SELECT

                    id,
                    topic,
                    content,
                    word_count,
                    content_type,
                    created_at

                FROM generated_content

                WHERE id = :report_id

                AND user_id = :user_id

                LIMIT 1
            """),
            {
                "report_id": report_id,
                "user_id": user_id
            }
        ).mappings().first()


        if not report:

            return jsonify({
                "success": False,
                "message": "Report not found."
            }), 404


        # =================================================
        # AI PLAGIARISM
        # =================================================

        ai_report = db.session.execute(
            text("""
                SELECT
                    score,
                    matched_sources,
                    created_at
                FROM plagiarism_history
                WHERE user_id = :user_id
                AND topic = :topic
                AND check_type = 'AI'
                ORDER BY id DESC
                LIMIT 1
            """),
            {
                "user_id": user_id,
                "topic": report["topic"]
            }
        ).mappings().first()


        # =================================================
        # HUMANIZED PLAGIARISM
        # =================================================

        human_report = db.session.execute(
            text("""
                SELECT
                    score,
                    matched_sources,
                    created_at
                FROM plagiarism_history
                WHERE user_id = :user_id
                AND topic = :topic
                AND check_type = 'HUMANIZED'
                ORDER BY id DESC
                LIMIT 1
            """),
            {
                "user_id": user_id,
                "topic": report["topic"]
            }
        ).mappings().first()


        ai_sources = []

        human_sources = []


        if ai_report:

            ai_sources = parse_sources(
                ai_report["matched_sources"]
            )


        if human_report:

            human_sources = parse_sources(
                human_report["matched_sources"]
            )


        return jsonify({

            "success": True,

            "report": {

                "id": report["id"],

                "topic": report["topic"] or "",

                "content": report["content"] or "",

                "word_count": report["word_count"] or 0,

                "content_type": report["content_type"] or "",

                "created_at": format_datetime(
                    report["created_at"]
                ),

                "ai_score": (
                    float(ai_report["score"])
                    if ai_report
                    and ai_report["score"] is not None
                    else None
                ),

                "ai_sources": ai_sources,

                "humanized_score": (
                    float(human_report["score"])
                    if human_report
                    and human_report["score"] is not None
                    else None
                ),

                "humanized_sources": human_sources

            }

        })


    except Exception as e:

        print("\n========== SINGLE REPORT ERROR ==========")

        traceback.print_exc()

        return jsonify({

            "success": False,

            "message": str(e)

        }), 500


# =========================================================
# DELETE REPORT
# =========================================================

def delete_report_api(report_id):

    try:

        user_id = session.get("user_id")

        if not user_id:

            return jsonify({
                "success": False,
                "message": "User session not found."
            }), 401


        result = db.session.execute(
            text("""
                DELETE FROM generated_content

                WHERE id = :report_id

                AND user_id = :user_id
            """),
            {
                "report_id": report_id,
                "user_id": user_id
            }
        )


        if result.rowcount == 0:

            db.session.rollback()

            return jsonify({
                "success": False,
                "message": "Report not found."
            }), 404


        db.session.commit()


        return jsonify({

            "success": True,

            "message":
                "Report deleted successfully."

        })


    except Exception as e:

        db.session.rollback()

        print("\n========== DELETE REPORT ERROR ==========")

        traceback.print_exc()

        return jsonify({

            "success": False,

            "message": str(e)

        }), 500
