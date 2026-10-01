from flask import jsonify, render_template, request, session
import traceback

from app.database import db
from app.user.services.seo_service import (
    analyze_seo,
    get_content_by_id,
    get_seo_history,
    get_user_content,
    save_seo_analysis
)


# =========================================================
# SEO PAGE
# =========================================================

def seo_analysis_page():
    return render_template("user/seo_analysis.html")


# =========================================================
# GET ALL AI + HUMANIZED CONTENT OF LOGGED-IN USER
# =========================================================

def seo_my_content_api():
    user_email = session.get("user_email")

    if not user_email:
        return jsonify({
            "success": False,
            "message": "User session not found.",
            "data": []
        }), 401

    try:
        contents = get_user_content(user_email)

        return jsonify({
            "success": True,
            "data": contents
        })

    except Exception as error:
        db.session.rollback()
        print("SEO CONTENT ERROR:", error)
        traceback.print_exc()

        return jsonify({
            "success": False,
            "message": "Unable to load your content.",
            "data": []
        }), 500


# =========================================================
# SOURCE HELPERS
# =========================================================

def _positive_id(value):
    if value is None or value == "" or isinstance(value, bool):
        return None

    try:
        value = int(value)
    except (TypeError, ValueError):
        return None

    return value if value > 0 else None


def _request_source(data):
    raw_source = str(data.get("source_type") or "").strip().lower()

    # Backward compatibility with the old AI-only frontend.
    if not raw_source:
        raw_source = "ai" if data.get("content_id") else "manual"

    if raw_source not in {"ai", "humanized", "manual"}:
        raise ValueError("Invalid content source.")

    raw_id = data.get("source_id")

    if raw_id in (None, "") and raw_source == "ai":
        raw_id = data.get("content_id")

    source_id = _positive_id(raw_id)

    if raw_source != "manual" and source_id is None:
        raise ValueError("A valid content source ID is required.")

    return raw_source, source_id


# =========================================================
# GET SELECTED AI OR HUMANIZED CONTENT
# =========================================================

def seo_get_content_api():
    user_email = session.get("user_email")

    if not user_email:
        return jsonify({
            "success": False,
            "message": "User session not found."
        }), 401

    data = request.get_json(silent=True) or {}

    try:
        source_type, source_id = _request_source(data)

        if source_type == "manual":
            return jsonify({
                "success": False,
                "message": "Please select AI or Humanized content."
            }), 400

        content = get_content_by_id(
            source_id,
            user_email,
            source_type
        )

        if not content:
            return jsonify({
                "success": False,
                "message": "Content not found."
            }), 404

        return jsonify({
            "success": True,
            "data": content
        })

    except ValueError as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 400

    except Exception as error:
        db.session.rollback()
        print("SEO SELECTED CONTENT ERROR:", error)
        traceback.print_exc()

        return jsonify({
            "success": False,
            "message": "Unable to load selected content."
        }), 500


# =========================================================
# ANALYZE AND SAVE SEO REPORT
# =========================================================

def seo_analyze_api():
    user_email = session.get("user_email")

    if not user_email:
        return jsonify({
            "success": False,
            "message": "User session not found."
        }), 401

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "message": "Valid JSON data is required."
        }), 400

    text_fields = (
        "content",
        "keyword",
        "content_topic",
        "topic",
        "seo_title",
        "meta_description",
        "source_type"
    )

    for field in text_fields:
        value = data.get(field)

        if value is not None and not isinstance(value, str):
            return jsonify({
                "success": False,
                "message": f"{field} must be text."
            }), 400

    content = (data.get("content") or "").strip()
    keyword = (data.get("keyword") or "").strip()
    seo_title = (data.get("seo_title") or "").strip()
    meta_description = (
        data.get("meta_description") or ""
    ).strip()

    content_topic = (
        data.get("content_topic")
        or data.get("topic")
        or ""
    ).strip()

    if not content:
        return jsonify({
            "success": False,
            "message": "Content is required."
        }), 400

    if not keyword:
        return jsonify({
            "success": False,
            "message": "Target keyword is required."
        }), 400

    try:
        source_type, source_id = _request_source(data)

        # Verify that selected content belongs to the logged-in user.
        if source_type != "manual":
            selected_content = get_content_by_id(
                source_id,
                user_email,
                source_type
            )

            if not selected_content:
                return jsonify({
                    "success": False,
                    "message": "Content not found."
                }), 404

            content_topic = (
                selected_content.get("topic")
                or "Untitled Content"
            )

        else:
            source_id = None
            content_topic = (
                content_topic
                or seo_title
                or "Manual SEO Analysis"
            )

        result = analyze_seo(
            content=content,
            keyword=keyword,
            seo_title=seo_title,
            meta_description=meta_description,
            fallback_title=content_topic
        )

        # content_id is kept only for compatibility with old AI reports.
        legacy_content_id = (
            source_id if source_type == "ai" else None
        )

        save_seo_analysis({
            "user_email": user_email,
            "content_id": legacy_content_id,
            "source_type": source_type,
            "source_id": source_id,
            "content_topic": content_topic,
            "word_count": result.get("word_count", 0),
            "seo_score": result.get("seo_score", 0),
            "readability_score": result.get(
                "readability_score", 0
            ),
            "keyword_density": result.get(
                "keyword_density", 0
            ),
            "keyword_count": result.get("keyword_count", 0),
            "seo_status": result.get("seo_status", "")
        })

        return jsonify({
            "success": True,
            "message": (
                "SEO analysis completed and saved automatically."
            ),
            "data": result
        })

    except ValueError as error:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": str(error)
        }), 400

    except Exception:
        db.session.rollback()
        traceback.print_exc()

        return jsonify({
            "success": False,
            "message": "Unable to complete and save SEO analysis."
        }), 500


# =========================================================
# SEO HISTORY
# =========================================================

def seo_history_api():
    user_email = session.get("user_email")

    if not user_email:
        return jsonify({
            "success": False,
            "message": "User session not found.",
            "data": []
        }), 401

    try:
        history = get_seo_history(user_email)

        return jsonify({
            "success": True,
            "data": history
        })

    except Exception as error:
        db.session.rollback()
        print("SEO HISTORY ERROR:", error)
        traceback.print_exc()

        return jsonify({
            "success": False,
            "message": "Unable to load SEO history.",
            "data": []
        }), 500
