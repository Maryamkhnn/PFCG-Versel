from flask import render_template
from flask import request
from flask import jsonify
from flask import session
from flask import current_app
from sqlalchemy import text

from app.database import db
from app.user.services.content_service import (
    save_document,
    get_saved_documents,
    delete_document,
    delete_my_content
)


# =====================================
# Edit Content Page
# =====================================

def edit_content_page():

    return render_template(
        "user/edit_content.html"
    )


# =====================================
# My Content Page
# =====================================

def my_content_page():

    return render_template(
        "user/my_content.html"
    )
# ============================================================
# MY CONTENT API
# ORIGINAL + EDITED + HUMANIZED CONTENT
# ============================================================


def my_content_api():

    # ========================================================
    # LOGIN CHECK
    # ========================================================

    user_email = session.get("user_email")

    if not user_email:
        return jsonify({
            "success": False,
            "message": "Please login again."
        }), 401


    try:

        # ====================================================
        # GET USER ID
        # ====================================================

        user_row = db.session.execute(
            text("""
                SELECT id
                FROM users
                WHERE email = :email
                LIMIT 1
            """),
            {
                "email": user_email
            }
        ).mappings().first()


        if not user_row:
            return jsonify({
                "success": False,
                "message": "User account not found."
            }), 404


        user_id = user_row["id"]


        # ====================================================
        # CONTENT QUERY
        #
        # IMPORTANT:
        # Generated + Edited are NOT returned as two cards.
        #
        # If edited_content exists:
        #     show edited content
        #     badge = Edited
        #
        # Otherwise:
        #     show generated content
        #     badge = Original
        #
        # Humanized remains separate.
        # ====================================================

        rows = db.session.execute(
            text("""
                SELECT
                    gc.id AS record_id,

                    NULL AS secondary_id,

                    gc.id AS original_content_id,

                    CASE
                        WHEN ec.id IS NOT NULL
                        THEN 'edited'
                        ELSE 'original'
                    END AS source_type,

                    COALESCE(
                        ec.topic,
                        gc.topic,
                        'Untitled Content'
                    ) AS topic,

                    CASE
                        WHEN ec.id IS NOT NULL
                        THEN ec.content
                        ELSE gc.content
                    END AS content,

                    COALESCE(
                        ec.content_type,
                        gc.content_type,
                        'Content'
                    ) AS content_type,

                    CASE
                        WHEN ec.id IS NOT NULL
                        THEN ec.word_count
                        ELSE gc.word_count
                    END AS word_count,

                    CASE
                        WHEN ec.id IS NOT NULL
                        THEN COALESCE(
                            ec.updated_at,
                            ec.created_at,
                            gc.created_at
                        )
                        ELSE gc.created_at
                    END AS created_at

                FROM generated_content gc

                LEFT JOIN edited_content ec
                    ON ec.original_content_id = gc.id
                    AND (
                        ec.user_email = :email
                        OR ec.user_id = :user_id
                    )

                WHERE
                    gc.user_email = :email
                    OR gc.user_id = :user_id


                UNION ALL


                SELECT
                    hh.id AS record_id,

                    hh.id AS secondary_id,

                    NULL AS original_content_id,

                    'humanized' AS source_type,

                    COALESCE(
                        gc.topic,
                        'Humanized Content'
                    ) AS topic,

                    hh.humanized_content AS content,

                    COALESCE(
                        gc.content_type,
                        'Content'
                    ) AS content_type,

                    hh.word_count AS word_count,

                    hh.created_at AS created_at

                FROM humanized_history hh

                LEFT JOIN generated_content gc
                    ON gc.id = (
                        SELECT gc2.id
                        FROM generated_content gc2
                        WHERE
                            (
                                gc2.user_email = :email
                                OR gc2.user_id = :user_id
                            )
                        ORDER BY gc2.created_at DESC
                        LIMIT 1
                    )

                WHERE
                    hh.user_email = :email
                    OR hh.user_id = :user_id

                ORDER BY created_at DESC
            """),
            {
                "email": user_email,
                "user_id": user_id
            }
        ).mappings().all()


        # ====================================================
        # SAVED DOCUMENTS
        # ====================================================

        saved_rows = db.session.execute(
            text("""
                SELECT
                    content,
                    content_type
                FROM saved_documents
                WHERE user_id = :user_id
            """),
            {
                "user_id": user_id
            }
        ).mappings().all()


        saved_lookup = set()

        for saved in saved_rows:

            saved_lookup.add((
                (saved["content"] or "").strip(),
                (saved["content_type"] or "Content").strip()
            ))


        # ====================================================
        # BUILD RESPONSE
        # ====================================================

        content_list = []


        for row in rows:

            source_type = (
                row["source_type"] or "original"
            ).strip().lower()


            content = (
                row["content"] or ""
            ).strip()


            content_type = (
                row["content_type"] or "Content"
            ).strip()


            # -----------------------------------------------
            # DISPLAY LABEL
            # -----------------------------------------------

            if source_type == "edited":

                version_label = "Edited"

            elif source_type == "humanized":

                version_label = "Humanized"

            else:

                version_label = "Original"


            # -----------------------------------------------
            # EDIT ID
            #
            # Original + Edited both use generated_content ID.
            # Editor service then automatically loads edited
            # version when one exists.
            # -----------------------------------------------

            if source_type in {
                "original",
                "edited"
            }:

                edit_id = row["original_content_id"]

            else:

                edit_id = None


            # -----------------------------------------------
            # UNIQUE CARD KEY
            # -----------------------------------------------

            if source_type == "humanized":

                content_key = (
                    f"humanized-{row['record_id']}"
                )

            else:

                content_key = (
                    f"content-{row['original_content_id']}"
                )


            # -----------------------------------------------
            # SAVED STATUS
            # -----------------------------------------------

            is_saved = (
                content,
                content_type
            ) in saved_lookup


            # -----------------------------------------------
            # DATE
            # -----------------------------------------------

            created_at = row["created_at"]

            if created_at:

                try:
                    created_at_value = (
                        created_at.isoformat()
                    )

                except AttributeError:
                    created_at_value = str(
                        created_at
                    )

            else:
                created_at_value = None


            # -----------------------------------------------
            # WORD COUNT FALLBACK
            # -----------------------------------------------

            word_count = row["word_count"]

            if word_count is None:
                word_count = len(
                    content.split()
                )


            # -----------------------------------------------
            # RESPONSE ITEM
            # -----------------------------------------------

            content_list.append({

                "id": row["record_id"],

                "edit_id": edit_id,

                "original_content_id":
                    row["original_content_id"],

                "content_key": content_key,

                "source_type": source_type,

                "version_label": version_label,

                "topic":
                    row["topic"]
                    or "Untitled Content",

                "content": content,

                "content_type": content_type,

                "word_count": word_count,

                "is_saved": is_saved,

                "created_at": created_at_value
            })


        return jsonify({
            "success": True,
            "data": content_list
        })


    except Exception as error:

        db.session.rollback()

        print(
            "MY CONTENT ERROR:",
            error
        )

        return jsonify({
            "success": False,
            "message": "Unable to load your content."
        }), 500
def saved_documents_page():

    user_id = session.get("user_id")

    documents = get_saved_documents(user_id)

    return render_template(

        "user/saved_documents.html",

        documents=documents

    )


# =====================================
# Save Document API
# =====================================

def save_document_api():

    try:

        data = request.get_json(force=True)

        result = save_document(

            session.get("user_id"),

            data

        )

        return jsonify(result)

    except Exception as e:

        return jsonify({

            "success": False,

            "message": str(e)

        })


# =====================================
# Delete Document API
# =====================================

def delete_document_api(document_id):

    data = request.get_json(
        silent=True
    ) or {}


    source_type = str(
        data.get(
            "source_type",
            "original"
        )
    ).strip().lower()


    result = delete_my_content(
    session.get("user_id"),
    document_id,
    source_type,
    session.get("user_email")
    )


    status_code = (
        200
        if result.get("success")
        else 400
    )


    return jsonify(
        result
    ), status_code