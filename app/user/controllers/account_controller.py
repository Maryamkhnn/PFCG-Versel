from functools import wraps
from io import BytesIO
from pathlib import Path
from uuid import uuid4
import warnings
from flask import send_file
from sqlalchemy import text
from PIL import Image, ImageOps, UnidentifiedImageError

from flask import (
    render_template,
    redirect,
    url_for,
    request,
    jsonify,
    session,
    current_app
)

from app.database import db

from app.user.services.account_service import (
    AccountError,
    require_user,
    get_account,
    update_account,
    change_account_password,
    update_account_picture,
    get_account_settings,
    update_account_preferences
)


def account_page():
    return render_template("user/account.html")


def legacy_account_page():
    return redirect(url_for("user.account"))


def account_api(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        user_email = session.get("user_email")

        if not user_email:
            return jsonify({
                "success": False,
                "message": "Please sign in again."
            }), 401

        try:
            return function(user_email, *args, **kwargs)

        except AccountError as error:
            db.session.rollback()

            return jsonify({
                "success": False,
                "message": str(error)
            }), error.status

        except Exception:
            db.session.rollback()
            current_app.logger.exception("Account request failed")

            return jsonify({
                "success": False,
                "message": "Unable to complete the account request."
            }), 500

    return wrapped


def json_payload():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        raise AccountError("Valid JSON data is required.")

    return data


@account_api
def get_account_api(user_email):
    return jsonify({
        "success": True,
        "data": get_account(user_email)
    })


@account_api
def update_account_api(user_email):
    profile = update_account(user_email, json_payload())

    session["user_name"] = profile["name"]

    return jsonify({
        "success": True,
        "message": "Your profile has been updated.",
        "data": profile
    })


@account_api
def change_account_password_api(user_email):
    change_account_password(user_email, json_payload())

    return jsonify({
        "success": True,
        "message": "Your password has been changed."
    })


@account_api
def upload_account_picture_api(user_email):
    require_user(user_email)

    file = request.files.get("profile_picture")

    if file is None or not file.filename:
        raise AccountError("Please select a profile photo.")

    max_bytes = 2 * 1024 * 1024
    raw = file.read(max_bytes + 1)

    if not raw or len(raw) > max_bytes:
        raise AccountError("Choose an image no larger than 2 MB.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter(
                "error",
                Image.DecompressionBombWarning
            )

            with Image.open(BytesIO(raw)) as source:
                if source.format not in {"PNG", "JPEG", "WEBP"}:
                    raise AccountError(
                        "Choose a JPG, PNG or WEBP image."
                    )

                width, height = source.size

                if width * height > 16_000_000:
                    raise AccountError(
                        "This image is too large. Choose a smaller image."
                    )

                source.load()

                picture = ImageOps.exif_transpose(source).convert("RGB")
                picture.thumbnail((512, 512))

                output = BytesIO()
                picture.save(
                    output,
                    format="JPEG",
                    quality=90
                )

    except AccountError:
        raise

    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning
    ):
        raise AccountError(
            "Please select a valid JPG, PNG or WEBP image."
        )

    picture_url = url_for(
        "user.account_photo",
        v=uuid4().hex
    )

    result = update_account_picture(
        user_email,
        picture_url,
        output.getvalue()
    )

    return jsonify({
        "success": True,
        "message": "Your profile photo has been updated.",
        "data": result
    })
@account_api
def get_account_settings_api(user_email):
    return jsonify({
        "success": True,
        "data": get_account_settings(user_email)
    })


@account_api
def save_account_preferences_api(user_email):
    update_account_preferences(user_email, json_payload())

    return jsonify({
        "success": True,
        "message": "Preferences saved successfully."
    })
@account_api
def get_account_picture_api(user_email):
    user = require_user(user_email)

    picture_bytes = db.session.execute(
        text("""
            SELECT profile_picture_data
            FROM users
            WHERE id = :user_id
        """),
        {"user_id": user.id}
    ).scalar_one_or_none()

    if not picture_bytes:
        raise AccountError("Profile photo not found.", 404)

    response = send_file(
        BytesIO(bytes(picture_bytes)),
        mimetype="image/jpeg",
        download_name="profile.jpg",
        max_age=0
    )

    response.headers["Cache-Control"] = "private, no-store"

    return response