from sqlalchemy import text

from app.database import db


# =====================================================
# GET SAVED DOCUMENTS
# =====================================================

def get_saved_documents(user_id):

    if not user_id:
        return []


    try:

        result = db.session.execute(
            text("""
                SELECT
                    id,
                    topic,
                    content,
                    content_type,
                    word_count,
                    created_at
                FROM saved_documents
                WHERE user_id = :user_id
                ORDER BY id DESC
            """),
            {
                "user_id": user_id
            }
        )


        rows = result.mappings().all()


        return [

            {
                "id": row["id"],

                "topic":
                    row["topic"] or "Untitled Document",

                "content":
                    row["content"] or "",

                "content_type":
                    row["content_type"] or "Document",

                "word_count":
                    row["word_count"] or 0,

                "created_at":
                    str(row["created_at"])
                    if row["created_at"]
                    else ""

            }

            for row in rows

        ]


    except Exception as e:

        print(
            "GET SAVED DOCUMENTS SERVICE ERROR:",
            e
        )

        raise


# =====================================================
# DELETE SAVED DOCUMENT
# =====================================================

def delete_saved_document(
    user_id,
    document_id
):

    if not user_id:

        return {
            "success": False,
            "message":
                "User session not found."
        }


    if not document_id:

        return {
            "success": False,
            "message":
                "Document ID is required."
        }


    try:

        result = db.session.execute(

            text("""
                DELETE FROM saved_documents
                WHERE id = :id
                AND user_id = :user_id
            """),

            {
                "id": document_id,
                "user_id": user_id
            }

        )


        # ---------------------------------------------
        # DOCUMENT NOT FOUND
        # ---------------------------------------------

        if result.rowcount == 0:

            db.session.rollback()

            return {

                "success": False,

                "message":
                    "Saved document not found."

            }


        # ---------------------------------------------
        # COMMIT DELETE
        # ---------------------------------------------

        db.session.commit()


        return {

            "success": True,

            "message":
                "Document removed successfully."

        }


    except Exception as e:

        db.session.rollback()


        print(
            "DELETE SAVED DOCUMENT ERROR:",
            e
        )


        return {

            "success": False,

            "message":
                "Unable to remove saved document."

        }