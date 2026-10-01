from flask import (
    render_template,
    request,
    jsonify,
    session
)

from app.user.services.feedback_service import (
    create_feedback,
    get_user_feedback,
    get_latest_user_feedback
)


# ============================================================
# FEEDBACK PAGE
# ============================================================

def feedback_page():

    return render_template(
        "user/feedback.html"
    )


# ============================================================
# SUBMIT FEEDBACK
# ============================================================

def submit_feedback_api():

    user_email = session.get("user_email")

    if not user_email:

        return jsonify({
            "success": False,
            "message": "User session not found."
        }), 401

    data = request.get_json(
        silent=True
    ) or {}

    feedback_type = str(
        data.get("feedback_type", "")
    ).strip()

    subject = str(
        data.get("subject", "")
    ).strip()

    message = str(
        data.get("message", "")
    ).strip()

    rating = data.get("rating")


    # ========================================================
    # VALIDATION
    # ========================================================

    if not feedback_type:

        return jsonify({
            "success": False,
            "message": "Please select feedback type."
        }), 400


    if not subject:

        return jsonify({
            "success": False,
            "message": "Please enter feedback subject."
        }), 400


    if not message:

        return jsonify({
            "success": False,
            "message": "Please write your feedback."
        }), 400


    try:

        rating = int(rating)

    except (
        TypeError,
        ValueError
    ):

        return jsonify({
            "success": False,
            "message": "Invalid rating."
        }), 400


    if rating < 1 or rating > 5:

        return jsonify({
            "success": False,
            "message": "Rating must be between 1 and 5."
        }), 400


    try:

        feedback_id = create_feedback(
            user_email,
            feedback_type,
            subject,
            message,
            rating
        )

        return jsonify({

            "success": True,

            "message":
                "Feedback submitted successfully.",

            "id": feedback_id

        })


    except Exception as e:

        print(
            "SUBMIT FEEDBACK ERROR:",
            e
        )

        db_error = str(e)

        return jsonify({

            "success": False,

            "message":
                "Unable to submit feedback.",

            "error":
                db_error

        }), 500


# ============================================================
# GET USER FEEDBACK
# ============================================================

def get_feedback_api():

    user_email = session.get("user_email")

    if not user_email:

        return jsonify({
            "success": False,
            "message": "User session not found."
        }), 401


    try:

        feedback = get_user_feedback(
            user_email
        )

        return jsonify({

            "success": True,

            "data": feedback,

            "count": len(feedback)

        })


    except Exception as e:

        print(
            "GET FEEDBACK ERROR:",
            e
        )

        return jsonify({

            "success": False,

            "message":
                "Unable to load feedback."

        }), 500


# ============================================================
# GET LATEST FEEDBACK
# ============================================================

def get_latest_feedback_api():

    user_email = session.get("user_email")

    if not user_email:

        return jsonify({
            "success": False,
            "message": "User session not found."
        }), 401


    try:

        feedback = get_latest_user_feedback(
            user_email
        )

        return jsonify({

            "success": True,

            "data": feedback

        })


    except Exception as e:

        print(
            "LATEST FEEDBACK ERROR:",
            e
        )

        return jsonify({

            "success": False,

            "message":
                "Unable to load feedback."

        }), 500