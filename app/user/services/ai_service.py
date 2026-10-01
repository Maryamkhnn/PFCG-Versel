import re

from sqlalchemy import text

from app.database import db
from flask import session, current_app
from app.user.services.prompt_service import (
    ROLE_PROMPTS,
    CONTENT_TYPES,
    BLOCKED_KEYWORDS
)

from app.user.services.generation_service import (
    generate_content
)

def generate_ai_content(data):

    # REQUEST VALIDATION

    if not isinstance(data, dict):
        return {
            "success": False,
            "message": "Please submit valid content settings."
        }

    prompt = data.get("prompt", "")

    if not isinstance(prompt, str):
        return {
            "success": False,
            "message": "Please enter your topic as text."
        }

    prompt = prompt.strip()

    if not prompt:
        return {
            "success": False,
            "message": (
                "Please enter a clear topic or writing request, "
                "such as 'Causes and effects of air pollution'."
            )
        }

    if len(prompt) > 3000:
        return {
            "success": False,
            "message": (
                "Please keep your topic or instructions "
                "within 3,000 characters."
            )
        }


    # ROLE AND CONTENT TYPE

    role = data.get("role", "Student")
    content_type = data.get("content_type", "Blog")

    if not isinstance(role, str) or role not in ROLE_PROMPTS:
        return {
            "success": False,
            "message": "Please select a valid role."
        }

    if (
        not isinstance(content_type, str)
        or content_type not in CONTENT_TYPES
    ):
        return {
            "success": False,
            "message": "Please select a valid content type."
        }

    role_prompt = ROLE_PROMPTS[role]
    content_prompt = CONTENT_TYPES[content_type]

    # WORD COUNT
    raw_word_count = data.get("word_count", 500)
    if (
        isinstance(raw_word_count, bool)
        or not isinstance(raw_word_count, (int, str))
    ):
        return {
            "success": False,
            "message": "Word count must be a whole number."
        }

    try:
        word_count = int(raw_word_count)
    except (TypeError, ValueError):
        return {
            "success": False,
            "message": "Word count must be a whole number."
        }

    if not 100 <= word_count <= 3000:
        return {
            "success": False,
            "message": "Please choose between 100 and 3,000 words."
        }
    # BASIC LANGUAGE SCREEN
    if not re.search(r"[A-Za-z]", prompt):
        return {
            "success": False,
            "message": "Please enter a clear topic in English."
        }

    # EXISTING BLOCKED-KEYWORD POLICY
    

    blocked_topic = any(
        re.search(
            r"(?<!\w)" + re.escape(keyword) + r"(?!\w)",
            prompt,
            flags=re.IGNORECASE
        )
        for keyword in BLOCKED_KEYWORDS
        if keyword
    )

    if blocked_topic:
        return {
            "success": False,
            "message": (
                "This topic is not supported. "
                "Please choose a different topic."
            )
        }

    # GENERATE
    # generate_content() runs validate_generation_topic().
    # Do not call that validation again here.

    try:
        generated_text = generate_content(
            topic=prompt,
            role_prompt=role_prompt,
            content_prompt=content_prompt,
            word_count=word_count
        )

    except ValueError as error:
        # Clear validation message for the frontend.
        return {
            "success": False,
            "message": str(error)
        }

    except Exception:
        current_app.logger.exception(
            "Content generation failed"
        )

        return {
            "success": False,
            "message": (
                "Unable to complete content generation right now. "
                "Please try again."
            )
        }

    if (
        not isinstance(generated_text, str)
        or not generated_text.strip()
    ):
        return {
            "success": False,
            "message": (
                "No content was generated. Please try again."
            )
        }

    generated_text = generated_text.strip()
    generated_words = len(generated_text.split())

    # DASHBOARD STATS
    # Only reached after successful generation.
    user_email = session.get("user_email")

    if user_email:
        try:
            existing = db.session.execute(
                text("""
                    SELECT id
                    FROM dashboard_stats
                    WHERE user_email = :email
                """),
                {"email": user_email}
            ).fetchone()

            if existing:
                db.session.execute(
                    text("""
                        UPDATE dashboard_stats
                        SET
                            generated_count = generated_count + 1,
                            total_words = total_words + :words
                        WHERE user_email = :email
                    """),
                    {
                        "email": user_email,
                        "words": generated_words
                    }
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
                        (
                            :email,
                            1,
                            :words,
                            0,
                            0,
                            0
                        )
                    """),
                    {
                        "email": user_email,
                        "words": generated_words
                    }
                )

            db.session.commit()

        except Exception:
            db.session.rollback()

            current_app.logger.exception(
                "Dashboard generation statistics update failed"
            )

    # ========================================================
    # FINAL RESPONSE — EXISTING FORMAT
    # ========================================================

    return {
        "success": True,
        "content": generated_text,
        "word_count": generated_words
    }