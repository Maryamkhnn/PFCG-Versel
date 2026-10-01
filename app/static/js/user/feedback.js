document.addEventListener(
    "DOMContentLoaded",
    function () {

        "use strict";


        // ==================================================
        // PAGE AND API URLS
        // ==================================================

        const page =
            document.getElementById("feedbackPage");

        if (!page) {
            return;
        }

        const submitUrl =
            page.dataset.submitUrl;

        const historyUrl =
            page.dataset.historyUrl;


        // ==================================================
        // FORM ELEMENTS
        // ==================================================

        const form =
            document.getElementById("feedbackForm");

        const feedbackType =
            document.getElementById("feedbackType");

        const feedbackRating =
            document.getElementById("feedbackRating");

        const feedbackSubject =
            document.getElementById("feedbackSubject");

        const feedbackMessage =
            document.getElementById("feedbackMessage");

        const characterCount =
            document.getElementById("feedbackCharacters");

        const submitButton =
            document.getElementById("submitFeedbackBtn");

        const csrfInput =
            document.getElementById("feedbackCsrf");


        // ==================================================
        // HISTORY ELEMENTS
        // ==================================================

        const historyList =
            document.getElementById("feedbackHistoryList");

        const historyCount =
            document.getElementById("feedbackHistoryCount");

        const searchInput =
            document.getElementById("searchFeedback");

        const pagination =
            document.getElementById("feedbackPagination");

        const previousButton =
            document.getElementById("feedbackPrev");

        const nextButton =
            document.getElementById("feedbackNext");

        const pageNumber =
            document.getElementById("feedbackPageNumber");


        // ==================================================
        // TOAST ELEMENTS
        // ==================================================

        const toast =
            document.getElementById("feedbackToast");

        const toastText =
            document.getElementById("feedbackToastText");

        const closeToastButton =
            document.getElementById("closeFeedbackToast");


        // ==================================================
        // STATE
        // ==================================================

        let allFeedback = [];
        let filteredFeedback = [];
        let currentPage = 1;

        const perPage = 5;

        let toastTimer = null;


        // ==================================================
        // TOAST
        // ==================================================

        function showToast(message, type = "success") {

            if (!toast || !toastText) {
                return;
            }

            if (toastTimer) {
                clearTimeout(toastTimer);
            }

            toastText.textContent = message;

            toast.className =
                `feedback-toast ${type}`;

            toast.hidden = false;

            toastTimer = setTimeout(
                function () {
                    toast.hidden = true;
                },
                4000
            );
        }


        function hideToast() {

            if (toast) {
                toast.hidden = true;
            }

            if (toastTimer) {
                clearTimeout(toastTimer);
                toastTimer = null;
            }
        }


        closeToastButton?.addEventListener(
            "click",
            hideToast
        );


        // ==================================================
        // CHARACTER COUNTER
        // ==================================================

        function updateCharacterCount() {

            const length =
                feedbackMessage?.value.length || 0;

            if (characterCount) {
                characterCount.textContent =
                    `${length} / 2000`;
            }
        }


        feedbackMessage?.addEventListener(
            "input",
            updateCharacterCount
        );


        // ==================================================
        // DATE FORMAT
        // ==================================================

        function formatDate(value) {

            if (!value) {
                return "Date unavailable";
            }

            const normalizedValue =
                String(value).replace(" ", "T");

            const date =
                new Date(normalizedValue);

            if (Number.isNaN(date.getTime())) {
                return value;
            }

            return date.toLocaleString(
                "en-PK",
                {
                    year: "numeric",
                    month: "short",
                    day: "2-digit",
                    hour: "2-digit",
                    minute: "2-digit"
                }
            );
        }


        // ==================================================
        // REQUEST HELPER
        // ==================================================

        async function requestJson(
            url,
            options = {}
        ) {

            const response =
                await fetch(url, {
                    credentials: "same-origin",
                    ...options
                });

            const responseText =
                await response.text();

            let result = {};

            if (responseText) {

                try {
                    result = JSON.parse(responseText);
                } catch {
                    throw new Error(
                        "Server returned an invalid response."
                    );
                }
            }

            if (!response.ok) {

                throw new Error(
                    result.message
                    || result.error
                    || "Request failed."
                );
            }

            return result;
        }


        // ==================================================
        // CREATE ELEMENT HELPER
        // ==================================================

        function createElement(
            tagName,
            className,
            text
        ) {

            const element =
                document.createElement(tagName);

            if (className) {
                element.className = className;
            }

            if (text !== undefined) {
                element.textContent = text;
            }

            return element;
        }


        // ==================================================
        // RENDER ONE FEEDBACK
        // ==================================================

        function createFeedbackCard(item) {

            const card =
                createElement(
                    "article",
                    "feedback-history-item"
                );

            const header =
                createElement(
                    "div",
                    "feedback-history-item-header"
                );

            const titleArea =
                createElement(
                    "div",
                    "feedback-history-title"
                );

            const subject =
                createElement(
                    "h3",
                    "",
                    item.subject || "No Subject"
                );

            const type =
                createElement(
                    "p",
                    "feedback-history-type",
                    item.feedback_type
                    || "General Feedback"
                );

            titleArea.append(
                subject,
                type
            );

            const status =
                createElement(
                    "span",
                    "fb-status",
                    item.status || "New"
                );

            const safeStatus = String(
                item.status || "New"
            )
                .toLowerCase()
                .replace(/[^a-z0-9]+/g, "-");

            status.classList.add(safeStatus);

            header.append(
                titleArea,
                status
            );


            const message =
                createElement(
                    "p",
                    "feedback-history-message",
                    item.message || "No feedback message."
                );


            const meta =
                createElement(
                    "div",
                    "feedback-history-meta"
                );

            const rating =
                createElement(
                    "span",
                    "",
                    `Rating: ${item.rating || 0}/5`
                );

            const date =
                createElement(
                    "span",
                    "",
                    formatDate(item.created_at)
                );

            meta.append(
                rating,
                date
            );


            const replyBox =
                createElement(
                    "div",
                    "feedback-history-reply"
                );

            const replyTitle =
                createElement(
                    "strong",
                    "",
                    "Admin reply"
                );

            const reply =
                createElement(
                    "p",
                    "",
                    item.admin_reply
                    || "No admin reply yet."
                );

            replyBox.append(
                replyTitle,
                reply
            );


            card.append(
                header,
                message,
                meta,
                replyBox
            );

            return card;
        }


        // ==================================================
        // RENDER HISTORY
        // ==================================================

        function renderHistory() {

            if (!historyList || !historyCount) {
                return;
            }

            historyList.replaceChildren();

            const totalItems =
                filteredFeedback.length;

            const totalPages = Math.max(
                1,
                Math.ceil(totalItems / perPage)
            );

            currentPage = Math.min(
                currentPage,
                totalPages
            );

            currentPage = Math.max(
                currentPage,
                1
            );

            historyCount.textContent =
                `${totalItems} feedback submission`
                + (totalItems === 1 ? "" : "s");

            if (totalItems === 0) {

                const emptyState =
                    createElement(
                        "div",
                        "feedback-empty-state"
                    );

                const icon =
                    createElement(
                        "i",
                        "far fa-comment-dots"
                    );

                const title =
                    createElement(
                        "h3",
                        "",
                        "No feedback found"
                    );

                const text =
                    createElement(
                        "p",
                        "",
                        "Your submitted feedback will appear here."
                    );

                emptyState.append(
                    icon,
                    title,
                    text
                );

                historyList.appendChild(
                    emptyState
                );

                historyList.setAttribute(
                    "aria-busy",
                    "false"
                );

                if (pagination) {
                    pagination.hidden = true;
                }

                return;
            }

            const startIndex =
                (currentPage - 1) * perPage;

            const pageItems =
                filteredFeedback.slice(
                    startIndex,
                    startIndex + perPage
                );

            pageItems.forEach(
                function (item) {

                    historyList.appendChild(
                        createFeedbackCard(item)
                    );
                }
            );

            historyList.setAttribute(
                "aria-busy",
                "false"
            );

            if (pagination) {
                pagination.hidden =
                    totalPages <= 1;
            }

            if (pageNumber) {
                pageNumber.textContent =
                    `Page ${currentPage} of ${totalPages}`;
            }

            if (previousButton) {
                previousButton.disabled =
                    currentPage === 1;
            }

            if (nextButton) {
                nextButton.disabled =
                    currentPage === totalPages;
            }
        }


        // ==================================================
        // FILTER HISTORY
        // ==================================================

        function filterHistory() {

            const searchValue = (
                searchInput?.value || ""
            )
                .trim()
                .toLowerCase();

            if (!searchValue) {

                filteredFeedback = [
                    ...allFeedback
                ];

            } else {

                filteredFeedback =
                    allFeedback.filter(
                        function (item) {

                            const searchableText = [
                                item.feedback_type,
                                item.subject,
                                item.message,
                                item.status,
                                item.admin_reply
                            ]
                                .filter(Boolean)
                                .join(" ")
                                .toLowerCase();

                            return searchableText.includes(
                                searchValue
                            );
                        }
                    );
            }

            currentPage = 1;

            renderHistory();
        }


        searchInput?.addEventListener(
            "input",
            filterHistory
        );


        // ==================================================
        // LOAD HISTORY
        // ==================================================

        async function loadFeedbackHistory() {

            if (!historyUrl) {
                throw new Error(
                    "Feedback history URL is missing."
                );
            }

            if (historyList) {

                historyList.setAttribute(
                    "aria-busy",
                    "true"
                );

                historyList.textContent =
                    "Loading feedback...";
            }

            try {

                const result =
                    await requestJson(
                        historyUrl,
                        {
                            method: "GET",
                            headers: {
                                "Accept":
                                    "application/json"
                            }
                        }
                    );

                if (result.success !== true) {

                    throw new Error(
                        result.message
                        || "Unable to load feedback."
                    );
                }

                allFeedback = Array.isArray(
                    result.data
                )
                    ? result.data
                    : [];

                filteredFeedback = [
                    ...allFeedback
                ];

                currentPage = 1;

                renderHistory();

            } catch (error) {

                console.error(
                    "Feedback history error:",
                    error
                );

                allFeedback = [];
                filteredFeedback = [];

                if (historyList) {

                    historyList.textContent =
                        "Unable to load feedback history.";

                    historyList.setAttribute(
                        "aria-busy",
                        "false"
                    );
                }

                if (historyCount) {
                    historyCount.textContent =
                        "Feedback history unavailable";
                }

                showToast(
                    error.message,
                    "error"
                );
            }
        }


        // ==================================================
        // SUBMIT FEEDBACK
        // ==================================================

        form?.addEventListener(
            "submit",
            async function (event) {

                event.preventDefault();

                const typeValue =
                    feedbackType.value.trim();

                const ratingValue =
                    Number(feedbackRating.value);

                const subjectValue =
                    feedbackSubject.value.trim();

                const messageValue =
                    feedbackMessage.value.trim();

                if (!typeValue) {

                    showToast(
                        "Please select feedback type.",
                        "error"
                    );

                    feedbackType.focus();
                    return;
                }

                if (
                    !Number.isInteger(ratingValue)
                    || ratingValue < 1
                    || ratingValue > 5
                ) {

                    showToast(
                        "Please select a valid rating.",
                        "error"
                    );

                    feedbackRating.focus();
                    return;
                }

                if (!subjectValue) {

                    showToast(
                        "Please enter feedback subject.",
                        "error"
                    );

                    feedbackSubject.focus();
                    return;
                }

                if (!messageValue) {

                    showToast(
                        "Please write your feedback.",
                        "error"
                    );

                    feedbackMessage.focus();
                    return;
                }

                if (!submitUrl) {

                    showToast(
                        "Feedback URL is missing.",
                        "error"
                    );

                    return;
                }

                const originalButtonContent =
                    submitButton.innerHTML;

                submitButton.disabled = true;

                submitButton.innerHTML = `
                    <i class="fas fa-spinner fa-spin"></i>
                    <span>Submitting...</span>
                `;

                const headers = {
                    "Accept": "application/json",
                    "Content-Type":
                        "application/json"
                };

                const csrfToken =
                    csrfInput?.value?.trim();

                if (csrfToken) {
                    headers["X-CSRFToken"] =
                        csrfToken;
                }

                try {

                    const result =
                        await requestJson(
                            submitUrl,
                            {
                                method: "POST",
                                headers: headers,
                                body: JSON.stringify({
                                    feedback_type:
                                        typeValue,
                                    subject:
                                        subjectValue,
                                    message:
                                        messageValue,
                                    rating:
                                        ratingValue
                                })
                            }
                        );

                    if (result.success !== true) {

                        throw new Error(
                            result.message
                            || "Unable to submit feedback."
                        );
                    }

                    showToast(
                        result.message
                        || "Feedback submitted successfully.",
                        "success"
                    );

                    form.reset();

                    updateCharacterCount();

                    await loadFeedbackHistory();

                } catch (error) {

                    console.error(
                        "Submit feedback error:",
                        error
                    );

                    showToast(
                        error.message
                        || "Unable to submit feedback.",
                        "error"
                    );

                } finally {

                    submitButton.disabled = false;

                    submitButton.innerHTML =
                        originalButtonContent;
                }
            }
        );


        // ==================================================
        // PAGINATION
        // ==================================================

        previousButton?.addEventListener(
            "click",
            function () {

                if (currentPage > 1) {

                    currentPage -= 1;

                    renderHistory();

                    historyList?.scrollIntoView({
                        behavior: "smooth",
                        block: "start"
                    });
                }
            }
        );


        nextButton?.addEventListener(
            "click",
            function () {

                const totalPages = Math.max(
                    1,
                    Math.ceil(
                        filteredFeedback.length
                        / perPage
                    )
                );

                if (currentPage < totalPages) {

                    currentPage += 1;

                    renderHistory();

                    historyList?.scrollIntoView({
                        behavior: "smooth",
                        block: "start"
                    });
                }
            }
        );


        // ==================================================
        // INITIAL LOAD
        // ==================================================

        updateCharacterCount();

        loadFeedbackHistory();
    }
);