from flask import request, jsonify, session
from sqlalchemy import text

from app.database import db

from app.user.services.plagiarism_service import check_plagiarism


def plagiarism_content():
    try:
        print("\n==============================================")
        print("          PLAGIARISM CHECK STARTED")
        print("==============================================")

        data = request.get_json(silent=True) or {}

        text_content = str(data.get("text", "") or "").strip()
        topic = str(data.get("topic", "") or "").strip()

        check_type = str(
            data.get("check_type", "AI") or "AI"
        ).upper().strip()

        if check_type not in ("AI", "HUMANIZED"):
            check_type = "AI"

        print("Topic:", topic)
        print("Check Type:", check_type)
        print("Text Length:", len(text_content))

        user_id = session.get("user_id")
        user_email = session.get("user_email")

        if not user_id:
            return jsonify({
                "success": False,
                "percentage": 0,
                "sources": [],
                "message": "User session not found."
            }), 401

        if not text_content:
            return jsonify({
                "success": True,
                "check_type": check_type,
                "percentage": 0,
                "plagiarism_percentage": 0,
                "score": 0,
                "sources": [],
                "checked_sentences": 0,
                "important_sentences": 0,
                "covered_sentences": 0,
                "uncovered_sentences": 0,
                "matched_sentences": 0,
                "coverage": 0,
                "source_count": 0,
                "status": "empty_text",
                "coverage_note": "No text was provided."
            })

        # Pass check_type into the plagiarism service
        result = check_plagiarism(
            text=text_content,
            topic=topic,
            check_type=check_type
        )

        percentage = result.get(
            "plagiarism_percentage",
            result.get("score", 0)
        )

        sources = result.get("sources", [])

        print("Final Plagiarism:", percentage)
        print("Matched Sources:", len(sources))
        print("Check Type Returned:", result.get("check_type"))
        print("Search Coverage:", result.get("coverage"))
        print("Checked Sentences:", result.get("checked_sentences"))
        print("Matched Sentences:", result.get("matched_sentences"))
        print("Status:", result.get("status"))

        # =====================================================
        # WORD COUNT
        # =====================================================

        word_count = len(text_content.split())

        print("Word Count:", word_count)

        # =====================================================
        # SAVE PLAGIARISM HISTORY
        # =====================================================

        try:
            db.session.execute(
                text("""
                    INSERT INTO plagiarism_history
                    (
                        user_id,
                        user_email,
                        score,
                        topic,
                        content,
                        matched_sources,
                        check_type,
                        word_count
                    )
                    VALUES
                    (
                        :user_id,
                        :user_email,
                        :score,
                        :topic,
                        :content,
                        :sources,
                        :check_type,
                        :word_count
                    )
                """),
                {
                    "user_id": user_id,
                    "user_email": user_email,
                    "score": percentage,
                    "topic": topic,
                    "content": text_content,
                    "sources": __import__("json").dumps(sources),
                    "check_type": check_type,
                    "word_count": word_count
                }
            )

            db.session.commit()

            print("Plagiarism history saved:", check_type)
            print("Saved Word Count:", word_count)

        except Exception as db_error:
            db.session.rollback()

            print(
                "PLAGIARISM HISTORY SAVE ERROR:",
                repr(db_error)
            )

        result["check_type"] = check_type

        return jsonify(result)

    except Exception as e:
        import traceback

        traceback.print_exc()

        try:
            db.session.rollback()
        except Exception:
            pass

        return jsonify({
            "success": False,
            "percentage": 0,
            "plagiarism_percentage": 0,
            "score": 0,
            "sources": [],
            "checked_sentences": 0,
            "important_sentences": 0,
            "covered_sentences": 0,
            "uncovered_sentences": 0,
            "matched_sentences": 0,
            "source_count": 0,
            "message": str(e)
        }), 500