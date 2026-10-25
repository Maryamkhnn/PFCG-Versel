from flask import render_template, jsonify, session, request
from sqlalchemy import text
from app.database import db
import traceback
import json
from urllib.parse import urlsplit

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

def selected_seo_report_page(user_email):
    raw_id = request.args.get("seo_id", "")

    try:
        report_id = int(raw_id)

        if report_id <= 0:
            raise ValueError

    except (TypeError, ValueError):
        return "Invalid SEO report ID.", 400

    row = db.session.execute(
        text("""
            SELECT
                id,
                content_topic,
                content,
                source_type,
                word_count,
                seo_score,
                readability_score,
                keyword_count,
                keyword_density,
                seo_status,
                report_json,
                created_at
            FROM seo_history
            WHERE id = :report_id
              AND user_email = :user_email
            LIMIT 1
        """),
        {
            "report_id": report_id,
            "user_email": user_email
        }
    ).mappings().first()

    if not row:
        return "SEO report not found.", 404

    saved = dict(row)
    payload = {}
    raw_payload = saved.get("report_json")

    if isinstance(raw_payload, dict):
        payload = raw_payload

    elif isinstance(raw_payload, str) and raw_payload.strip():
        try:
            parsed = json.loads(raw_payload)

            if isinstance(parsed, dict):
                payload = parsed

        except (TypeError, ValueError):
            payload = {}

    details = payload.get("report")

    if not isinstance(details, dict):
        details = {}

    checks = details.get("checks")

    if not isinstance(checks, list):
        checks = []

    checks = [
        check for check in checks
        if isinstance(check, dict)
    ]

    suggestions = details.get("suggestions")

    if not isinstance(suggestions, list):
        suggestions = []

    suggestions = [
        suggestion for suggestion in suggestions
        if isinstance(suggestion, str)
    ]

    saved["created_at"] = format_datetime(
        saved.get("created_at")
    )

    keyword = payload.get("keyword")
    content = payload.get("content")

    return render_template(
        "user/seo_report_detail.html",
        saved=saved,
        details=details,
        checks=checks,
        suggestions=suggestions,
        keyword=keyword if isinstance(keyword, str) else "",
        analyzed_content=(
            content if isinstance(content, str)
            else saved.get("content") or ""
        )
    )
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
                           )
                        ORDER BY sh.id DESC
                        LIMIT 1
                    ) AS readability_score,

                                       (
                        SELECT sh.keyword_density
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
def reports_page():
    user_id = session.get("user_id")
    user_email = session.get("user_email")

    if not user_id or not user_email:
        return "Please sign in again.", 401

    try:
        # Open the exact SEO report selected from history.
        if "seo_id" in request.args:
            return selected_seo_report_page(user_email)
        if "plagiarism_id" in request.args:
            return selected_plagiarism_report_page(user_id)

        # Otherwise show the existing Reports listing.
        rows = db.session.execute(
            text("""
                SELECT
                    id,
                    'plagiarism' AS report_type,
                    topic,
                    content,
                    check_type AS source_type,
                    word_count,
                    score AS plagiarism_score,
                    matched_sources,
                    NULL AS seo_score,
                    NULL AS readability_score,
                    NULL AS keyword_count,
                    NULL AS keyword_density,
                    NULL AS seo_status,
                    created_at
                FROM plagiarism_history
                WHERE user_id = :user_id

                UNION ALL

                SELECT
                    id,
                    'seo' AS report_type,
                    content_topic AS topic,
                    content,
                    source_type,
                    word_count,
                    NULL AS plagiarism_score,
                    NULL AS matched_sources,
                    seo_score,
                    readability_score,
                    keyword_count,
                    keyword_density,
                    seo_status,
                    created_at
                FROM seo_history
                WHERE user_email = :user_email

                ORDER BY created_at DESC, report_type ASC, id DESC
            """),
            {
                "user_id": user_id,
                "user_email": user_email
            }
        ).mappings().all()

        # Recover content for older SEO records without saved text.
        linked_rows = db.session.execute(
            text("""
                SELECT
                    sh.id,
                    CASE
                        WHEN LOWER(TRIM(sh.source_type)) = 'ai'
                            THEN gc.content
                        WHEN LOWER(TRIM(sh.source_type)) = 'humanized'
                            THEN hh.humanized_content
                        ELSE NULL
                    END AS linked_content
                FROM seo_history AS sh

                LEFT JOIN generated_content AS gc
                    ON gc.id = sh.source_id
                    AND gc.user_id = :user_id
                    AND LOWER(TRIM(sh.source_type)) = 'ai'

                LEFT JOIN humanized_history AS hh
                    ON hh.id = sh.source_id
                    AND hh.user_id = :user_id
                    AND LOWER(TRIM(sh.source_type)) = 'humanized'

                WHERE sh.user_email = :user_email
            """),
            {
                "user_id": user_id,
                "user_email": user_email
            }
        ).mappings().all()

        linked_content = {
            row["id"]: row["linked_content"] or ""
            for row in linked_rows
        }

        reports = []

        for row in rows:
            report = dict(row)

            if (
                report["report_type"] == "seo"
                and not (report["content"] or "").strip()
            ):
                report["content"] = linked_content.get(
                    report["id"], ""
                )

            source = str(
                report["source_type"] or "manual"
            ).strip().lower()

            report["source_label"] = {
                "ai": "AI Content",
                "humanized": "Humanized Content",
                "manual": "Manual Content"
            }.get(source, "Content")

            report["topic"] = (
                report["topic"] or "Untitled Content"
            )

            report["word_count"] = report["word_count"] or 0
            report["content"] = report["content"] or ""

            report["content_available"] = bool(
                report["content"].strip()
            )

            report["created_at"] = format_datetime(
                report["created_at"]
            )

            report["source_count"] = len(
                parse_sources(report["matched_sources"])
            )

            for field in (
                "plagiarism_score",
                "seo_score",
                "readability_score",
                "keyword_density"
            ):
                if report[field] is not None:
                    report[field] = float(report[field])

            reports.append(report)

        return render_template(
            "user/reports.html",
            reports=reports
        )

    except Exception:
        db.session.rollback()
        traceback.print_exc()

        return "Unable to load reports. Please try again.", 503
    
def selected_plagiarism_report_page(user_id):
    raw_id = request.args.get("plagiarism_id", "")

    try:
        report_id = int(raw_id)

        if report_id <= 0:
            raise ValueError

    except (TypeError, ValueError):
        return "Invalid plagiarism report ID.", 400

    row = db.session.execute(
        text("""
            SELECT
                id,
                topic,
                content,
                check_type,
                word_count,
                score,
                matched_sources,
                created_at
            FROM plagiarism_history
            WHERE id = :report_id
              AND user_id = :user_id
            LIMIT 1
        """),
        {
            "report_id": report_id,
            "user_id": user_id
        }
    ).mappings().first()

    if not row:
        return "Plagiarism report not found.", 404

    saved = dict(row)
    saved["created_at"] = format_datetime(saved["created_at"])

    raw_sources = parse_sources(saved.get("matched_sources"))

    if not isinstance(raw_sources, list):
        raw_sources = []

    sources = []

    for source in raw_sources:
        if not isinstance(source, dict):
            continue

        url = source.get("url")
        url = url.strip() if isinstance(url, str) else ""

        # Permit only ordinary public web-link schemes.
        try:
            parsed = urlsplit(url)

            if (
                parsed.scheme.lower() not in {"http", "https"}
                or not parsed.hostname
            ):
                url = ""

        except ValueError:
            url = ""

        similarity = source.get("similarity")

        try:
            similarity = float(similarity)

            if not 0 <= similarity <= 100:
                similarity = None

        except (TypeError, ValueError):
            similarity = None

        def source_text(field):
            value = source.get(field)
            return value.strip() if isinstance(value, str) else ""

        sources.append({
            "title": source_text("title") or "Matched source",
            "url": url,
            "similarity": similarity,
            "matched_text": source_text("matched_text"),
            "source_text": source_text("source_text"),
            "reason": source_text("reason").replace("_", " "),
            "sentence_index": source.get("sentence_index"),
            "evidence_type": source_text(
                "evidence_type"
            ).replace("_", " ")
        })

    return render_template(
        "user/plagiarism_report_detail.html",
        saved=saved,
        sources=sources
    )