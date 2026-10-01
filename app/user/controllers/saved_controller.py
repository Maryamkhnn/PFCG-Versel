from flask import jsonify, session

from flask import jsonify, session

from app.user.services.content_service import (
    get_saved_documents
)


# ============================================================
# GET SAVED DOCUMENTS API
# ============================================================

def get_saved_documents_api():

    user_id = session.get("user_id")

    if not user_id:

        return jsonify({
            "success": False,
            "message": "Please sign in again."
        }), 401


    try:

        documents = get_saved_documents(
            user_id
        )


        return jsonify({
            "success": True,
            "data": documents,
            "count": len(documents)
        })


    except Exception as error:

        print(
            "GET SAVED DOCUMENTS API ERROR:",
            repr(error)
        )


        return jsonify({
            "success": False,
            "message": (
                "Unable to load saved documents."
            )
        }), 500
# =====================================================
# DELETE SAVED DOCUMENT API
# =====================================================

def delete_saved_document_api(
    document_id
):

    user_id = session.get("user_id")


    if not user_id:

        return jsonify({

            "success": False,

            "message":
                "User session not found."

        }), 401


    if not document_id:

        return jsonify({

            "success": False,

            "message":
                "Document ID is required."

        }), 400


    try:

        result = delete_saved_document(

            user_id,

            document_id

        )


        if not result.get("success"):

            return jsonify(result), 404


        return jsonify(result)


    except Exception as e:

        print(
            "DELETE SAVED DOCUMENT API ERROR:",
            e
        )


        return jsonify({

            "success": False,

            "message":
                "Unable to delete saved document."

        }), 500