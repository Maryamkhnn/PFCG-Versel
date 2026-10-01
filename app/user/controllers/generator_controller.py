import json
import time
from contextlib import closing
from datetime import datetime, timedelta

from flask import (
    Response,
    current_app,
    jsonify,
    render_template,
    request,
    session,
    stream_with_context,
)
from sqlalchemy import text
from app.user.services.generator_restriction_service import (
    add_restriction_notification,
    sync_generator_restriction,
)
from app.database import db
from app.models import User
from app.user.services.ai_service import generate_ai_content
from app.user.services.generation_service import humanize_text
from app.user.services.streaming_generation_service import (
    BlockedTopicError,
    stream_quick_draft,
    validate_stream_request,
)


def generator_page():
    return render_template("user/generator.html")


def record_blocked_attempt(user_id, category):
    """Record an attempt and suspend a normal user on the fourth in 24 hours."""
    try:
        # Lock this user's row so simultaneous requests cannot both miss
        # the fourth-attempt threshold.
        locked_user_id = db.session.execute(
            text("SELECT id FROM users WHERE id = :user_id FOR UPDATE"),
            {"user_id": user_id},
        ).scalar_one_or_none()

        if locked_user_id is None:
            raise RuntimeError("User not found while recording blocked attempt.")

        user = db.session.get(User, user_id, populate_existing=True)
        now = datetime.utcnow()

        db.session.execute(
            text("""
                INSERT INTO blocked_topic_attempts
                    (user_id, category, created_at)
                VALUES
                    (:user_id, :category, :created_at)
            """),
            {
                "user_id": user_id,
                "category": category,
                "created_at": now,
            },
        )

        attempts = db.session.execute(
            text("""
                SELECT COUNT(*)
                FROM blocked_topic_attempts
                WHERE user_id = :user_id
                  AND created_at >= :since
            """),
            {
                "user_id": user_id,
                "since": now - timedelta(hours=24),
            },
        ).scalar_one()

        if (
            attempts >= 4
            and (user.role or "user").lower() != "admin"
            and (
                user.generator_restricted_until is None
                or user.generator_restricted_until <= now
            )
        ):
            user.generator_restricted_until = (
                now + timedelta(hours=1)
            )

            add_restriction_notification(
                user_id,
                user.generator_restricted_until,
            )
        db.session.commit()
        
        return (
            user.generator_restricted_until is not None
            and user.generator_restricted_until > now
        )

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Unable to record blocked topic attempt")
        raise
def _get_active_user(user_id):
    sync_generator_restriction(user_id)

    user = db.session.get(
        User,
        user_id,
        populate_existing=True,
    )

    if user is None:
        return None

    now = datetime.utcnow()

    if (
        (user.status or "").lower() == "suspended"
        and user.suspended_until is not None
        and user.suspended_until <= now
    ):
        user.status = "active"
        user.suspended_until = None
        user.status_reason = None
        user.status_changed_at = now
        db.session.commit()

    return user



def generate_content():
    user_id = session.get("user_id")
    

    if not user_id:
        return jsonify(
            success=False,
            message="Your session has expired. Please sign in again.",
        ), 401

    user = _get_active_user(user_id)

    if user is None:
        return jsonify(
            success=False,
            message="Account not found. Please sign in again.",
        ), 401
    email = user.email
    if (user.status or "active").lower() != "active":
        return jsonify(
            success=False,
            message="Your account is suspended. Please try again later.",
        ), 403
    if (
        user.generator_restricted_until is not None
        and user.generator_restricted_until > datetime.utcnow()
    ):
        return jsonify(
            success=False,
            message="Content generation is restricted for 1 hour.",
        ), 403

    try:
        settings = validate_stream_request(request.get_json(silent=True))

    except BlockedTopicError as error:
        current_app.logger.warning(
            "BLOCKED HANDLER HIT: user_id=%s category=%s",
            user_id,
            error.category,
        )

        try:
            suspended = record_blocked_attempt(user_id, error.category)
        except Exception:
            return jsonify(
                success=False,
                message="Unable to process this request. Please try again later.",
            ), 500

        if suspended:
            return jsonify(
                success=False,
                message=(
                    "Content generation is restricted for 1 hour "
                    "after repeated blocked topic attempts."
                ),
            ), 403

        return jsonify(
            success=False,
            message="This topic is not allowed.",
        ), 400

    except ValueError as error:
        current_app.logger.warning(
            "VALUE ERROR HANDLER HIT: %s",
            type(error).__name__,
        )

        return jsonify(
            success=False,
            message=str(error),
            suggestions=getattr(error, "suggestions", []),
        ), 400
        return jsonify(success=False, message=str(error)), 400
    except RuntimeError as error:
        return jsonify(
            success=False,
            message=str(error)
        ), 503

    # Detailed mode: return one JSON response.
    if "application/x-ndjson" not in request.headers.get("Accept", ""):
        started = time.monotonic()

        try:
            result = generate_ai_content(settings)

            if result.get("success"):
                if (
                    not isinstance(result.get("content"), str)
                    or not result["content"].strip()
                ):
                    raise RuntimeError("The generator did not return content.")

                result["word_count"] = len(result["content"].split())
                result["id"] = _save_generated(
                    settings,
                    result,
                    user_id,
                    email,
                )

            return jsonify(result)

        except Exception:
            db.session.rollback()
            current_app.logger.exception("Detailed generation failed")
            return jsonify(
                success=False,
                message="Unable to complete generation. Please try again.",
            ), 500

        finally:
            current_app.logger.info(
                "PFCG detailed total: %.2fs",
                time.monotonic() - started,
            )

    # Quick mode: return NDJSON events.
    def line(event):
        return json.dumps(event, ensure_ascii=False) + "\n"

    @stream_with_context
    def events():
        started = time.monotonic()

        try:
            yield line({
                "type": "status",
                "message": (
                    "Preparing a quick draft. "
                    "External sources are not checked."
                ),
            })

            with closing(stream_quick_draft(settings)) as draft_events:
                for event in draft_events:
                    if event["type"] == "ready":
                        yield line({
                            "type": "status",
                            "message": "Saving the completed draft…",
                        })

                        content_id = _save_generated(
                            settings,
                            event,
                            user_id,
                            email,
                            update_stats=True,
                        )

                        yield line({
                            "type": "done",
                            "success": True,
                            "id": content_id,
                            "content": event["content"],
                            "word_count": event["word_count"],
                            "externally_verified": False,
                            "message": (
                                "Draft generated and saved. "
                                "Review factual claims before use."
                            ),
                        })
                        return

                    yield line(event)

        except GeneratorExit:
            db.session.rollback()
            raise

        except ValueError as error:
            db.session.rollback()
            yield line({"type": "error", "message": str(error)})

        except Exception as error:
            db.session.rollback()
            current_app.logger.exception("Quick generation failed")

            if getattr(error, "status_code", None) == 429:
                message = (
                    "The generation limit has been reached. "
                    "Please try again later."
                )
            elif (
                isinstance(error, TimeoutError)
                or "Timeout" in type(error).__name__
            ):
                message = "Generation timed out. Please try again shortly."
            elif type(error) is RuntimeError:
                message = str(error)
            else:
                message = (
                    "Unable to complete and save this draft. "
                    "Please try again."
                )

            yield line({"type": "error", "message": message})

        finally:
            current_app.logger.info(
                "PFCG quick total: %.2fs",
                time.monotonic() - started,
            )

    return Response(
        events(),
        content_type="application/x-ndjson; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )

    current_app.logger.warning(
        "GENERATE SESSION user_id=%s email_present=%s",
        session.get("user_id"),
        bool(session.get("user_email")),
    )

def humanize_content():
    user_id = session.get("user_id")
    email = session.get("user_email")

    if not user_id or not email:
        return jsonify(
            success=False,
            message="Your session has expired. Please sign in again.",
        ), 401

    user = _get_active_user(user_id)

    if user is None:
        return jsonify(
            success=False,
            message="Account not found. Please sign in again.",
        ), 401

    if (user.status or "active").lower() != "active":
        return jsonify(
            success=False,
            message="Your account is suspended. Please try again later.",
        ), 403

    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not isinstance(data.get("content"), str):
        return jsonify(
            success=False,
            message="Please provide valid content.",
        ), 400

    original = data["content"].strip()

    if not original:
        return jsonify(
            success=False,
            message="No content provided for humanization.",
        ), 400

    try:
        result = humanize_text(original)

        if result.get("success"):
            rewritten = result.get("content", "").strip()

            if not rewritten:
                raise RuntimeError("Humanized content is empty.")

            words = len(rewritten.split())

            db.session.execute(
                text("""
                    INSERT INTO humanized_history
                        (
                            user_id,
                            user_email,
                            original_content,
                            humanized_content,
                            word_count
                        )
                    VALUES
                        (
                            :uid,
                            :email,
                            :original,
                            :rewritten,
                            :words
                        )
                """),
                {
                    "uid": user_id,
                    "email": email,
                    "original": original,
                    "rewritten": rewritten,
                    "words": words,
                },
            )
            db.session.commit()
            result["word_count"] = words

        return jsonify(result)

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Humanization failed")
        return jsonify(
            success=False,
            message="Unable to complete humanization. Please try again.",
        ), 500


def _save_generated(settings, result, user_id, email, update_stats=False):
    inserted = db.session.execute(
        text("""
            INSERT INTO generated_content
                (
                    user_id,
                    user_email,
                    topic,
                    content,
                    word_count,
                    content_type
                )
            VALUES
                (
                    :uid,
                    :email,
                    :topic,
                    :content,
                    :words,
                    :ctype
                )
        """),
        {
            "uid": user_id,
            "email": email,
            "topic": settings["prompt"],
            "content": result["content"],
            "words": result["word_count"],
            "ctype": settings["content_type"],
        },
    )

    content_id = inserted.lastrowid

    if update_stats:
        # Keep the existing Quick mode statistics behavior.
        existing = db.session.execute(
            text("""
                SELECT id
                FROM dashboard_stats
                WHERE user_email = :email
                FOR UPDATE
            """),
            {"email": email},
        ).first()

        if existing:
            db.session.execute(
                text("""
                    UPDATE dashboard_stats
                    SET generated_count = COALESCE(generated_count, 0) + 1,
                        total_words = COALESCE(total_words, 0) + :words
                    WHERE user_email = :email
                """),
                {"email": email, "words": result["word_count"]},
            )
        else:
            db.session.execute(
                text("""
                    INSERT INTO dashboard_stats
                        (
                            user_email,
                            generated_count,
                            total_words,
                            humanized_count,
                            reports_count,
                            saved_count
                        )
                    VALUES
                        (:email, 1, :words, 0, 0, 0)
                """),
                {"email": email, "words": result["word_count"]},
            )

    db.session.commit()
    return content_id