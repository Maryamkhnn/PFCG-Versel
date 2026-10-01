document.addEventListener("DOMContentLoaded", function () {

    console.log("Generated Content JS Loaded");

    // =====================================================
    // ELEMENTS
    // =====================================================

    const contentModal = document.getElementById("contentModal");

    const modalTopic = document.getElementById("modalTopic");
    const modalUser = document.getElementById("modalUser");
    const modalType = document.getElementById("modalType");
    const modalWords = document.getElementById("modalWords");
    const modalContent = document.getElementById("modalContent");

    const closeContentModal =
        document.getElementById("closeContentModal");

    const modalCloseBtn =
        document.getElementById("modalCloseBtn");


    // =====================================================
    // CHECK ELEMENTS
    // =====================================================

    console.log("Modal:", contentModal);
    console.log(
        "View Buttons:",
        document.querySelectorAll(".view-content-btn").length
    );


    // =====================================================
    // OPEN CONTENT
    // =====================================================

    async function openContent(contentId) {

        console.log("Opening content ID:", contentId);

        if (!contentId) {
            alert("Content ID is missing.");
            return;
        }

        if (!contentModal) {
            console.error("Content modal not found.");
            alert("Content modal not found.");
            return;
        }


        // =================================================
        // SHOW MODAL
        // =================================================

        contentModal.classList.add("show");
        document.body.classList.add("modal-open");


        // =================================================
        // LOADING
        // =================================================

        if (modalTopic) {
            modalTopic.textContent = "Loading...";
        }

        if (modalUser) {
            modalUser.textContent = "-";
        }

        if (modalType) {
            modalType.textContent = "-";
        }

        if (modalWords) {
            modalWords.textContent = "0";
        }

        if (modalContent) {
            modalContent.textContent = "Loading content...";
        }


        try {

            // =================================================
            // API
            // =================================================

            const apiUrl = `/admin/content/${contentId}`;

            console.log("Fetching:", apiUrl);


            const response = await fetch(apiUrl, {
                method: "GET",
                headers: {
                    "Accept": "application/json"
                },
                credentials: "same-origin"
            });


            console.log("Response status:", response.status);


            // =================================================
            // READ RESPONSE
            // =================================================

            const responseText = await response.text();

            console.log("Server response:", responseText);


            if (!response.ok) {

                throw new Error(
                    `Server returned ${response.status}`
                );

            }


            // =================================================
            // JSON
            // =================================================

            let data;

            try {

                data = JSON.parse(responseText);

            } catch (error) {

                console.error("JSON ERROR:", error);

                throw new Error(
                    "Server did not return valid JSON."
                );

            }


            console.log("Parsed data:", data);


            // =================================================
            // SUCCESS CHECK
            // =================================================

            if (!data.success) {

                throw new Error(
                    data.message ||
                    "Unable to load generated content."
                );

            }


            if (!data.content) {

                throw new Error(
                    "No generated content received."
                );

            }


            const content = data.content;


            // =================================================
            // DISPLAY DATA
            // =================================================

            if (modalTopic) {

                modalTopic.textContent =
                    content.topic || "Generated Content";

            }


            if (modalUser) {

                modalUser.textContent =
                    content.user_email || "-";

            }


            if (modalType) {

                modalType.textContent =
                    content.content_type || "Blog";

            }


            if (modalWords) {

                modalWords.textContent =
                    content.word_count || "0";

            }


            if (modalContent) {

                modalContent.textContent =
                    content.content ||
                    "No content available.";

            }


            console.log("Content displayed successfully.");

        }

        catch (error) {

            console.error(
                "VIEW CONTENT ERROR:",
                error
            );


            if (modalContent) {

                modalContent.textContent =
                    "Unable to load content.";

            }

            alert(
                error.message ||
                "Unable to load content."
            );

        }

    }


    // =====================================================
    // VIEW BUTTONS
    // =====================================================

    // Event delegation - works even if buttons are
    // loaded/re-rendered later.

    document.addEventListener("click", function (event) {

        const button =
            event.target.closest(".view-content-btn");


        if (!button) {
            return;
        }


        event.preventDefault();
        event.stopPropagation();


        const contentId =
            button.getAttribute("data-id");


        console.log(
            "VIEW BUTTON CLICKED:",
            contentId
        );


        openContent(contentId);

    });


    // =====================================================
    // CLOSE MODAL
    // =====================================================

    function closeModal() {

        if (contentModal) {

            contentModal.classList.remove("show");

        }

        document.body.classList.remove("modal-open");

    }


    // =====================================================
    // CLOSE BUTTON
    // =====================================================

    if (closeContentModal) {

        closeContentModal.addEventListener(
            "click",
            closeModal
        );

    }


    if (modalCloseBtn) {

        modalCloseBtn.addEventListener(
            "click",
            closeModal
        );

    }


    // =====================================================
    // CLICK OUTSIDE MODAL
    // =====================================================

    if (contentModal) {

        contentModal.addEventListener(
            "click",
            function (event) {

                if (
                    event.target === contentModal
                ) {

                    closeModal();

                }

            }
        );

    }


    // =====================================================
    // ESC KEY
    // =====================================================

    document.addEventListener(
        "keydown",
        function (event) {

            if (
                event.key === "Escape" &&
                contentModal &&
                contentModal.classList.contains("show")
            ) {

                closeModal();

            }

        }
    );

});