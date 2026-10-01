from sqlalchemy import text

from app.database import db


# ============================================================
# SAVE DOCUMENT
# ============================================================

def save_document(user_id, data):

    if not user_id:

        return {
            "success": False,
            "message": "User session not found."
        }

    if not isinstance(data, dict):

        return {
            "success": False,
            "message": "Invalid document data."
        }


    topic = str(
        data.get("topic", "")
    ).strip()


    content = str(
        data.get("content", "")
    ).strip()


    content_type = str(
        data.get("content_type", "Blog")
    ).strip()


    source_type = str(
        data.get("source_type", "ai")
    ).strip().lower()


    if not topic:
        topic = "Untitled Content"


    if not content:

        return {
            "success": False,
            "message": "There is no content to save."
        }


    if not content_type:
        content_type = "Blog"


    if source_type not in {
        "ai",
        "humanized"
    }:

        return {
            "success": False,
            "message": "Invalid content source."
        }


    word_count = len(
        content.split()
    )


    try:

        # ----------------------------------------------------
        # GET USER EMAIL
        # ----------------------------------------------------

        user_email = db.session.execute(
            text("""
                SELECT email

                FROM users

                WHERE id = :user_id

                LIMIT 1
            """),
            {
                "user_id": user_id
            }
        ).scalar()


        if not user_email:

            return {
                "success": False,
                "message": "User account not found."
            }


        # ----------------------------------------------------
        # INSERT SAVED DOCUMENT
        # ----------------------------------------------------

        result = db.session.execute(
            text("""
                INSERT INTO saved_documents
                (
                    user_id,
                    user_email,
                    topic,
                    content,
                    content_type,
                    source_type,
                    word_count
                )
                VALUES
                (
                    :user_id,
                    :user_email,
                    :topic,
                    :content,
                    :content_type,
                    :source_type,
                    :word_count
                )
            """),
            {
                "user_id": user_id,
                "user_email": user_email,
                "topic": topic,
                "content": content,
                "content_type": content_type,
                "source_type": source_type,
                "word_count": word_count
            }
        )


        db.session.commit()


        source_label = (
            "Humanized content"
            if source_type == "humanized"
            else "AI content"
        )


        return {
            "success": True,
            "message": (
                f"{source_label} saved successfully."
            ),
            "document_id": result.lastrowid,
            "source_type": source_type,
            "word_count": word_count
        }


    except Exception as error:

        db.session.rollback()

        print(
            "SAVE DOCUMENT ERROR:",
            repr(error)
        )

        return {
            "success": False,
            "message": "Unable to save document."
        }


# ============================================================
# GET SAVED DOCUMENTS
# ============================================================

def get_saved_documents(user_id):

    if not user_id:
        return []


    try:

        documents = db.session.execute(
            text("""
                SELECT
                    id,
                    topic,
                    content,
                    content_type,
                    source_type,
                    word_count,
                    created_at

                FROM saved_documents

                WHERE user_id = :user_id

                ORDER BY
                    created_at DESC,
                    id DESC
            """),
            {
                "user_id": user_id
            }
        ).mappings().all()


        return [
            {
                "id": row["id"],

                "topic": (
                    row["topic"]
                    or "Untitled Content"
                ),

                "content": (
                    row["content"]
                    or ""
                ),

                "content_type": (
                    row["content_type"]
                    or "Document"
                ),

                "source_type": (
                    row["source_type"]
                    or "ai"
                ),

                "word_count": (
                    row["word_count"]
                    or 0
                ),

                "created_at": (
                    row["created_at"].isoformat()
                    if row["created_at"]
                    else None
                )
            }
            for row in documents
        ]


    except Exception as error:

        db.session.rollback()

        print(
            "GET SAVED DOCUMENTS ERROR:",
            repr(error)
        )

        raise


# ============================================================
# DELETE SAVED DOCUMENT
# ============================================================

def delete_document(
    user_id,
    document_id
):

    if not user_id or not document_id:

        return {
            "success": False,
            "message": "Invalid user or document ID."
        }


    try:

        result = db.session.execute(
            text("""
                DELETE FROM saved_documents

                WHERE id = :document_id
                  AND user_id = :user_id
            """),
            {
                "document_id": document_id,
                "user_id": user_id
            }
        )


        if result.rowcount == 0:

            db.session.rollback()

            return {
                "success": False,
                "message": "Saved document not found."
            }


        db.session.commit()


        return {
            "success": True,
            "message": (
                "Saved document deleted successfully."
            )
        }


    except Exception as error:

        db.session.rollback()

        print(
            "DELETE SAVED DOCUMENT ERROR:",
            repr(error)
        )

        return {
            "success": False,
            "message": (
                "Unable to delete saved document."
            )
        }
def delete_my_content(user_id, document_id, source_type, user_email=None):
    source_type = str(source_type or "").strip().lower()

    if not user_id or not document_id:
        return {
            "success": False,
            "message": "Invalid user or document ID."
        }

    if source_type not in {"original", "edited", "humanized"}:
        return {
            "success": False,
            "message": "Invalid content source."
        }

    params = {
        "document_id": document_id,
        "user_id": user_id,
        "user_email": user_email or ""
    }

    try:
        # Humanized record: delete only that record.
        if source_type == "humanized":
            result = db.session.execute(
                text("""
                    DELETE FROM humanized_history
                    WHERE id = :document_id
                      AND (
                          user_id = :user_id
                          OR LOWER(TRIM(user_email)) =
                             LOWER(TRIM(:user_email))
                      )
                """),
                params
            )

            if result.rowcount == 0:
                db.session.rollback()
                return {
                    "success": False,
                    "message": "Humanized content not found."
                }

            db.session.commit()
            return {
                "success": True,
                "message": "Humanized content deleted."
            }

        # First confirm that this AI content belongs to this user.
        original = db.session.execute(
            text("""
                SELECT id
                FROM generated_content
                WHERE id = :document_id
                  AND (
                      user_id = :user_id
                      OR LOWER(TRIM(user_email)) =
                         LOWER(TRIM(:user_email))
                  )
                LIMIT 1
            """),
            params
        ).scalar()

        if original is None:
            db.session.rollback()
            return {
                "success": False,
                "message": "AI content not found."
            }

        # Editor versions must be removed before the edited copy.
        db.session.execute(
            text("""
                DELETE FROM editor_versions
                WHERE content_id = :document_id
                  AND ( 
                     LOWER(TRIM(user_email)) =
                         LOWER(TRIM(:user_email))
                  )
            """),
            params
        )

        edited_result = db.session.execute(
            text("""
                DELETE FROM edited_content
                WHERE original_content_id = :document_id
                  AND (
                      user_id = :user_id
                      OR LOWER(TRIM(user_email)) =
                         LOWER(TRIM(:user_email))
                  )
            """),
            params
        )

        # Edited card: retain the AI original.
        if source_type == "edited":
            if edited_result.rowcount == 0:
                db.session.rollback()
                return {
                    "success": False,
                    "message": "Edited content not found."
                }

            db.session.commit()
            return {
                "success": True,
                "message": "Edited copy deleted. AI original remains."
            }

        # Original AI card: delete the original too.
        result = db.session.execute(
            text("""
                DELETE FROM generated_content
                WHERE id = :document_id
                  AND (
                      user_id = :user_id
                      OR LOWER(TRIM(user_email)) =
                         LOWER(TRIM(:user_email))
                  )
            """),
            params
        )

        if result.rowcount == 0:
            db.session.rollback()
            return {
                "success": False,
                "message": "AI content not found."
            }

        db.session.commit()
        return {
            "success": True,
            "message": "AI content deleted."
        }

    except Exception:
        db.session.rollback()
        raise