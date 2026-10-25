
from flask import jsonify, render_template, request, session, current_app
from app.database import db
from app.user.services.seo_service import (
    analyze_seo,
    get_content_by_id,
    get_seo_history,
    get_user_content,
    save_seo_analysis,
    apply_ai_metadata_scoring,
)

def _error(message, status=400, include_data=False):
    data = {"success": False, "message": message}
    if include_data:
        data["data"] = []
    return jsonify(data), status


def _current_user_email():
    return session.get("user_email")


def _positive_id(value):
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return None
    try:
        number = int(value)
        return number if number > 0 else None
    except (ValueError, TypeError):
        return None


def _request_source(data):
    source_type = str(data.get("source_type") or ("ai" if data.get("content_id") else "manual")).strip().lower()
    if source_type not in {"ai", "humanized", "manual"}:
        raise ValueError("Invalid content source.")
    source_id = _positive_id(data.get("source_id") or data.get("content_id"))
    if source_type != "manual" and source_id is None:
        raise ValueError("A valid content source ID is required.")
    return source_type, source_id


def seo_analysis_page():
    return render_template("user/seo_analysis.html")


def seo_my_content_api():
    email = _current_user_email()
    if not email:
        return _error("User session not found.", 401, True)
    try:
        return jsonify(success=True, data=get_user_content(email))
    except Exception:
        db.session.rollback()
        current_app.logger.exception("SEO content list failed")
        return _error("Unable to load your content.", 500, True)


def seo_get_content_api():
    email = _current_user_email()
    if not email:
        return _error("User session not found.", 401)
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _error("Valid JSON data is required.")
    try:
        kind, source_id = _request_source(data)
        if kind == "manual":
            return _error("Please select AI or Humanized content.")
        content = get_content_by_id(source_id, email, kind)
        if not content:
            return _error("Content not found.", 404)
        return jsonify(success=True, data=content)
    except ValueError as error:
        return _error(str(error))
    except Exception:
        db.session.rollback()
        current_app.logger.exception("SEO document load failed")
        return _error("Unable to load selected content.", 500)


def seo_analyze_api():
    email = _current_user_email()
    if not email:
        return _error("User session not found.", 401)
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _error("Valid JSON data is required.")
    for field in ("content", "keyword", "content_topic", "topic", "seo_title", "meta_description", "source_type"):
        if data.get(field) is not None and not isinstance(data[field], str):
            return _error(f"{field} must be text.")
    content = (data.get("content") or "").strip()
    keyword = (data.get("keyword") or "").strip()
    title = (data.get("seo_title") or "").strip()
    meta = (data.get("meta_description") or "").strip()
    if len(title) > 300 or len(meta) > 2000:
        return _error("Title limit is 300 characters; description limit is 2,000.")
    try:
        kind, source_id = _request_source(data)
        topic = (data.get("content_topic") or data.get("topic") or "").strip()
        fallback = ""
        if kind != "manual":
            selected = get_content_by_id(source_id, email, kind)
            if not selected:
                return _error("Content not found.", 404)
            topic = selected.get("topic") or "Untitled Content"
            fallback = selected.get("topic") or ""
        else:
            source_id = None
            topic = title or topic or "Manual SEO Analysis"
        result = analyze_seo(content, keyword, title, meta, fallback)
        try:
            from app.user.services.ai_service import (
                review_seo_content
            )

            result["ai_review"] = review_seo_content(
                content=content,
                keyword=keyword,
                seo_title=result.get("seo_title", ""),
                meta_description=result.get("meta_description", "")
            )

        except Exception:
            current_app.logger.exception(
                "SEO AI review unavailable"
            )

            result["ai_review"] = {
                "status": "unavailable",
                "message": (
                    "AI review is temporarily unavailable. "
                    "Your measured analysis is still available."
                ),
                "checks": []
            }
        result = apply_ai_metadata_scoring(result)

        save_seo_analysis({
            **result,
            "user_email": email,
            "content": content,
            "source_type": kind,
            "source_id": source_id,
            "content_topic": topic,
            "keyword": keyword,
            "report": result
        })
        return jsonify(success=True, message="SEO analysis completed and saved automatically.", data=result)
    except ValueError as error:
        db.session.rollback()
        return _error(str(error))
    except Exception:
        db.session.rollback()
        current_app.logger.exception("SEO analysis or save failed")
        return _error("Unable to complete and save SEO analysis. Check database migration and server logs.", 500)


def seo_history_api():
    email = _current_user_email()
    if not email:
        return _error("User session not found.", 401, True)
    try:
        return jsonify(success=True, data=get_seo_history(email))
    except Exception:
        db.session.rollback()
        current_app.logger.exception("SEO history failed")
        return _error("Unable to load SEO history.", 500, True)


def seo_suggest_metadata_api():
    if not session.get("user_email"):
        return jsonify({
            "success": False,
            "message": "Your session has expired. Please sign in again."
        }), 401

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "message": "Valid JSON data is required."
        }), 400

    try:
        from app.user.services.seo_metadata_service import (
            suggest_seo_metadata
        )

        metadata = suggest_seo_metadata(
            content=data.get("content"),
            keyword=data.get("keyword", "")
        )

        return jsonify({
            "success": True,
            "data": metadata
        })

    except ValueError as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 400

    except Exception:
        from flask import current_app

        current_app.logger.exception(
            "SEO metadata suggestion failed"
        )

        return jsonify({
            "success": False,
            "message": (
                "Unable to suggest a title and description right now. "
                "Please try again."
            )
        }), 502