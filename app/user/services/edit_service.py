import hashlib
import json
import re

from sqlalchemy import text

from app.database import db


# ============================================================
# EDIT CONFLICT
# ============================================================

class EditConflict(ValueError):
    pass


# ============================================================
# VALIDATE CONTENT ID
# ============================================================

def validate_id(value):

    if (
        isinstance(value, bool)
        or not isinstance(value, (int, str))
    ):
        raise ValueError("Invalid content ID.")

    value = str(value).strip()

    if (
        not re.fullmatch(r"[0-9]+", value)
        or int(value) < 1
    ):
        raise ValueError("Invalid content ID.")

    return int(value)


# ============================================================
# VALIDATE QUILL EDITOR DATA
# ============================================================

def validate_delta(delta):

    operations = (
        delta.get("ops")
        if isinstance(delta, dict)
        else None
    )

    if (
        not isinstance(operations, list)
        or not 1 <= len(operations) <= 50000
    ):
        raise ValueError("Invalid editor document.")

    allowed_choices = {
        "font": {
            "serif",
            "monospace"
        },
        "size": {
            "small",
            "large",
            "huge"
        },
        "align": {
            "center",
            "right",
            "justify"
        },
        "list": {
            "ordered",
            "bullet"
        },
        "lineheight": {
            "1",
            "1.5",
            "2",
            "2.5"
        }
    }

    cleaned_operations = []
    text_parts = []

    for operation in operations:

        if (
            not isinstance(operation, dict)
            or set(operation) - {
                "insert",
                "attributes"
            }
            or not isinstance(
                operation.get("insert"),
                str
            )
        ):
            raise ValueError(
                "Only text content is supported."
            )

        inserted_text = operation["insert"]

        if re.search(
            r"[\x00-\x08\x0b\x0c\x0e-\x1f"
            r"\ud800-\udfff\ufffe\uffff]",
            inserted_text
        ):
            raise ValueError(
                "Unsupported text character."
            )

        attributes = operation.get(
            "attributes",
            {}
        )

        if not isinstance(attributes, dict):
            raise ValueError("Invalid formatting.")

        cleaned_attributes = {}

        for key, item in attributes.items():

            if key in {
                "bold",
                "italic",
                "underline",
                "strike"
            }:
                valid = isinstance(item, bool)

            elif key == "header":
                valid = (
                    type(item) is int
                    and item in range(1, 4)
                )

            elif key == "indent":
                valid = (
                    type(item) is int
                    and item in range(0, 9)
                )

            elif key in allowed_choices:
                valid = (
                    isinstance(item, str)
                    and item in allowed_choices[key]
                )

            elif key in {
                "color",
                "background"
            }:
                valid = (
                    isinstance(item, str)
                    and re.fullmatch(
                        r"#[0-9a-fA-F]{3}"
                        r"(?:[0-9a-fA-F]{3})?",
                        item
                    )
                )

            else:
                valid = False

            if not valid:
                raise ValueError(
                    "Unsupported formatting: "
                    + key
                )

            cleaned_attributes[key] = item

        cleaned_operation = {
            "insert": inserted_text
        }

        if cleaned_attributes:
            cleaned_operation["attributes"] = (
                cleaned_attributes
            )

        cleaned_operations.append(
            cleaned_operation
        )

        text_parts.append(inserted_text)

    document_text = "".join(text_parts)

    if not document_text.endswith("\n"):
        raise ValueError(
            "Invalid editor document ending."
        )

    if len(document_text) > 500001:
        raise ValueError(
            "Document is too large."
        )

    return (
        {
            "ops": cleaned_operations
        },
        document_text[:-1]
    )


# ============================================================
# CREATE REVISION KEY
# ============================================================

def revision(row):

    raw = json.dumps(
        [
            row["content"] or "",
            row["editor_delta"] or ""
        ],
        ensure_ascii=False
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


# ============================================================
# GET OWNED CONTENT
# Supports both user_id and user_email.
# ============================================================

def owned(
    email,
    content_id,
    lock=False
):

    query = """
        SELECT
            gc.id,
            gc.user_id,
            gc.user_email,
            gc.topic,
            gc.content,
            gc.editor_delta,
            gc.content_type,
            gc.word_count,
            gc.created_at

        FROM generated_content AS gc

        WHERE gc.id = :content_id

          AND
          (
              LOWER(TRIM(gc.user_email))
                  = LOWER(TRIM(:email))

              OR gc.user_id = (
                  SELECT id
                  FROM users
                  WHERE LOWER(TRIM(email))
                      = LOWER(TRIM(:email))
                  LIMIT 1
              )
          )
    """

    if lock:
        query += " FOR UPDATE"

    return db.session.execute(
        text(query),
        {
            "content_id": validate_id(
                content_id
            ),
            "email": email
        }
    ).mappings().first()

def owned_edited(email, original_content_id, lock=False):

    query = """
        SELECT
            ec.id AS edited_id,
            ec.original_content_id AS id,
            ec.user_id,
            ec.user_email,
            ec.topic,
            ec.content,
            ec.editor_delta,
            ec.content_type,
            ec.word_count,
            ec.created_at,
            ec.updated_at

        FROM edited_content AS ec

        WHERE ec.original_content_id = :content_id

          AND (
                LOWER(TRIM(ec.user_email))
                    = LOWER(TRIM(:email))

                OR ec.user_id = (
                    SELECT id
                    FROM users
                    WHERE LOWER(TRIM(email))
                        = LOWER(TRIM(:email))
                    LIMIT 1
                )
          )
    """

    if lock:
        query += " FOR UPDATE"

    return db.session.execute(
        text(query),
        {
            "content_id": validate_id(original_content_id),
            "email": email
        }
    ).mappings().first()
# ============================================================
# SERIALIZE ONE CONTENT RECORD
# ============================================================

def serialize_content(row):

    result = {
        "id": row["id"],
        "topic": row["topic"],
        "content": row["content"] or "",
        "content_type": (
            row["content_type"]
            or "Content"
        ),
        "word_count": (
            row["word_count"]
            or 0
        ),
        "created_at": (
            row["created_at"].isoformat()
            if row["created_at"]
            else ""
        )
    }

    result["revision"] = revision(row)
    result["editor_delta"] = None

    stored_delta = row["editor_delta"]

    if stored_delta:

        try:

            decoded_delta = json.loads(
                stored_delta
            )

            valid_delta, plain_text = (
                validate_delta(
                    decoded_delta
                )
            )

            if plain_text == result["content"]:
                result["editor_delta"] = (
                    valid_delta
                )

        except (
            ValueError,
            TypeError,
            json.JSONDecodeError
        ):
            result["editor_delta"] = None

    return result


# ============================================================
# GET USER CONTENT LIST
# ============================================================

def get_editable_content(email):

    rows = db.session.execute(
        text("""
            SELECT
                gc.id,
                gc.topic,
                gc.content_type

            FROM generated_content AS gc

            WHERE
                LOWER(TRIM(gc.user_email))
                    = LOWER(TRIM(:email))

                OR gc.user_id = (
                    SELECT id
                    FROM users
                    WHERE LOWER(TRIM(email))
                        = LOWER(TRIM(:email))
                    LIMIT 1
                )

            ORDER BY
                gc.created_at DESC,
                gc.id DESC
        """),
        {
            "email": email
        }
    ).mappings().all()

    return [
        dict(row)
        for row in rows
    ]


def get_editable_content_by_id(email, content_id):

    content_id = validate_id(content_id)

    # --------------------------------------------------------
    # ORIGINAL DOCUMENT
    # --------------------------------------------------------

    original = owned(
        email,
        content_id
    )

    if not original:
        return None

    # --------------------------------------------------------
    # CHECK WHETHER AN EDITED COPY ALREADY EXISTS
    # --------------------------------------------------------

    edited = owned_edited(
        email,
        content_id
    )

    # --------------------------------------------------------
    # IF EDITED COPY EXISTS -> LOAD EDITED VERSION
    # --------------------------------------------------------

    if edited:

        row = {
            "id": original["id"],
            "user_id": edited["user_id"],
            "user_email": edited["user_email"],
            "topic": edited["topic"],
            "content": edited["content"],
            "editor_delta": edited["editor_delta"],
            "content_type": edited["content_type"],
            "word_count": edited["word_count"],
            "created_at": edited["created_at"]
        }

        result = serialize_content(row)

        result["is_edited"] = True
        result["edited_id"] = edited["edited_id"]

        return result

    # --------------------------------------------------------
    # OTHERWISE LOAD ORIGINAL
    # --------------------------------------------------------

    result = serialize_content(original)

    result["is_edited"] = False
    result["edited_id"] = None

    return result
def update_content(
    user_email,
    content_id,
    content,
    editor_delta=None,
    expected_revision=None,
    reason="Manual save"
):

    if (
        not isinstance(content, str)
        or not content.strip()
    ):
        raise ValueError(
            "Content cannot be empty."
        )

    valid_delta, plain_text = validate_delta(
        editor_delta
    )

    if plain_text != content:
        raise ValueError(
            "Content and formatting do not match."
        )

    if (
        not isinstance(expected_revision, str)
        or len(expected_revision) != 64
    ):
        raise ValueError(
            "Please reopen the document before saving."
        )

    encoded_delta = json.dumps(
        valid_delta,
        ensure_ascii=False,
        separators=(",", ":")
    )

    content_id = validate_id(content_id)

    try:

        # ====================================================
        # ORIGINAL MUST EXIST AND BELONG TO USER
        # ====================================================

        original = owned(
            user_email,
            content_id,
            lock=True
        )

        if not original:

            db.session.rollback()

            return {
                "success": False,
                "message": "Content not found."
            }

        # ====================================================
        # CHECK EXISTING EDITED COPY
        # ====================================================

        edited = owned_edited(
            user_email,
            content_id,
            lock=True
        )

        # ====================================================
        # DETERMINE CURRENT EDITOR DOCUMENT
        # ====================================================

        if edited:

            current_content = edited["content"] or ""
            current_delta = edited["editor_delta"] or ""

        else:

            current_content = original["content"] or ""
            current_delta = original["editor_delta"] or ""

        current_revision = revision({
            "content": current_content,
            "editor_delta": current_delta
        })

        # ====================================================
        # CONFLICT CHECK
        # ====================================================

        if current_revision != expected_revision:

            raise EditConflict(
                "This document changed elsewhere. "
                "Please reopen the latest version."
            )

        # ====================================================
        # NOTHING CHANGED
        # ====================================================

        if (
            content == current_content
            and encoded_delta == current_delta
        ):

            db.session.rollback()

            return {
                "success": True,
                "message": "No new changes to save.",
                "revision": expected_revision,
                "word_count": len(content.split())
            }

        word_count = len(content.split())

        # ====================================================
        # CREATE EDITED COPY ON FIRST SAVE
        # ====================================================

        if not edited:

            db.session.execute(
                text("""
                    INSERT INTO edited_content
                    (
                        original_content_id,
                        user_id,
                        user_email,
                        topic,
                        content,
                        editor_delta,
                        content_type,
                        word_count
                    )
                    VALUES
                    (
                        :original_content_id,
                        :user_id,
                        :user_email,
                        :topic,
                        :content,
                        :editor_delta,
                        :content_type,
                        :word_count
                    )
                """),
                {
                    "original_content_id": original["id"],
                    "user_id": original["user_id"],
                    "user_email": user_email,
                    "topic": original["topic"] or "Untitled Content",
                    "content": content,
                    "editor_delta": encoded_delta,
                    "content_type": original["content_type"] or "Content",
                    "word_count": word_count
                }
            )

        # ====================================================
        # OTHERWISE UPDATE EXISTING EDITED COPY
        # ====================================================

        else:

            db.session.execute(
                text("""
                    UPDATE edited_content

                    SET
                        content = :content,
                        editor_delta = :editor_delta,
                        word_count = :word_count,
                        updated_at = CURRENT_TIMESTAMP

                    WHERE original_content_id = :content_id
                      AND LOWER(TRIM(user_email))
                            = LOWER(TRIM(:user_email))
                """),
                {
                    "content": content,
                    "editor_delta": encoded_delta,
                    "word_count": word_count,
                    "content_id": original["id"],
                    "user_email": user_email
                }
            )

        # ====================================================
        # VERSION NUMBER
        # ====================================================

        latest_version_number = db.session.execute(
            text("""
                SELECT COALESCE(MAX(revision_number), 0)

                FROM editor_versions

                WHERE content_id = :content_id
                  AND LOWER(TRIM(user_email))
                        = LOWER(TRIM(:user_email))
            """),
            {
                "content_id": original["id"],
                "user_email": user_email
            }
        ).scalar() or 0

        # ====================================================
        # FIRST SAVE -> PRESERVE ORIGINAL
        # ====================================================

        if latest_version_number == 0:

            initial_delta = (
                serialize_content(original)["editor_delta"]
                or {
                    "ops": [
                        {
                            "insert":
                                (original["content"] or "") + "\n"
                        }
                    ]
                }
            )

            db.session.execute(
                text("""
                    INSERT INTO editor_versions
                    (
                        content_id,
                        user_email,
                        content,
                        editor_delta,
                        revision_number,
                        change_reason
                    )
                    VALUES
                    (
                        :content_id,
                        :user_email,
                        :content,
                        :editor_delta,
                        1,
                        'Original'
                    )
                """),
                {
                    "content_id": original["id"],
                    "user_email": user_email,
                    "content": original["content"] or "",
                    "editor_delta": json.dumps(
                        initial_delta,
                        ensure_ascii=False,
                        separators=(",", ":")
                    )
                }
            )

            latest_version_number = 1

        # ====================================================
        # SAVE CURRENT EDIT
        # ====================================================

        db.session.execute(
            text("""
                INSERT INTO editor_versions
                (
                    content_id,
                    user_email,
                    content,
                    editor_delta,
                    revision_number,
                    change_reason
                )
                VALUES
                (
                    :content_id,
                    :user_email,
                    :content,
                    :editor_delta,
                    :revision_number,
                    :change_reason
                )
            """),
            {
                "content_id": original["id"],
                "user_email": user_email,
                "content": content,
                "editor_delta": encoded_delta,
                "revision_number":
                    latest_version_number + 1,
                "change_reason": (
                    "Auto-save"
                    if reason == "Auto-save"
                    else "Manual save"
                )
            }
        )

        # ====================================================
        # NEW REVISION IS BASED ON EDITED COPY
        # ====================================================

        new_revision = revision({
            "content": content,
            "editor_delta": encoded_delta
        })

        db.session.commit()

        return {
            "success": True,
            "message": "Edited content saved successfully.",
            "revision": new_revision,
            "word_count": word_count,
            "is_edited": True
        }

    except Exception:

        db.session.rollback()
        raise
# ============================================================
# VERSION HISTORY
# ============================================================

def get_versions(
    email,
    content_id,
    before=None
):

    row = owned(email, content_id)

    if not row:
        return None

    cursor = (
        validate_id(before)
        if before
        else 9223372036854775807
    )

    rows = db.session.execute(
        text("""
            SELECT
                id,
                revision_number,
                change_reason,
                created_at
            FROM editor_versions
            WHERE content_id = :content_id
              AND LOWER(TRIM(user_email))
                  = LOWER(TRIM(:user_email))
              AND id < :cursor
            ORDER BY id DESC
            LIMIT 21
        """),
        {
            "content_id": row["id"],
            "user_email": email,
            "cursor": cursor
        }
    ).mappings().all()

    return {
        "items": [
            {
                "id": item["id"],
                "reason": (
                    item["change_reason"]
                    or "Version " + str(item["revision_number"])
                ),
                "revision_number": item["revision_number"],
                "created_at": (
                    item["created_at"].isoformat()
                    if item["created_at"]
                    else ""
                )
            }
            for item in rows[:20]
        ],
        "next": (
            rows[19]["id"]
            if len(rows) > 20
            else None
        )
    }


def get_version(
    email,
    content_id,
    version_id
):

    owner = owned(email, content_id)

    if not owner:
        return None

    row = db.session.execute(
        text("""
            SELECT
                content,
                editor_delta
            FROM editor_versions
            WHERE id = :version_id
              AND content_id = :content_id
              AND LOWER(TRIM(user_email))
                  = LOWER(TRIM(:user_email))
        """),
        {
            "version_id": validate_id(version_id),
            "content_id": owner["id"],
            "user_email": email
        }
    ).mappings().first()

    if not row:
        return None

    try:
        delta, plain_text = validate_delta(
            json.loads(row["editor_delta"])
        )
    except (TypeError, ValueError, json.JSONDecodeError):
        delta = {
            "ops": [
                {"insert": (row["content"] or "") + "\n"}
            ]
        }
        delta, plain_text = validate_delta(delta)

    return {
        "editor_delta": delta,
        "content": plain_text
    }
