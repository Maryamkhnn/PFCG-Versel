document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    const el = id => document.getElementById(id);
    const page = el("savedPage");

    if (!page) return;

    // Existing URLs from your current saved_documents.js.
    const LIST_URL = "/user/api/saved-documents";
    const REMOVE_URL = id =>
    `/user/api/saved-documents/${encodeURIComponent(id)}/remove`;

    const list = el("savedList");
    const preview = el("savedViewModal");
    const confirmation = el("savedConfirmModal");

    let documents = [];
    let currentPage = 1;
    let loading = false;
    let deleting = false;
    let pendingDocument = null;
    let loadError = "";
    let toastTimer;


    function notify(message, error = false) {
        clearTimeout(toastTimer);

        el("savedToastMessage").textContent = message;
        el("savedToast").classList.toggle("error", error);
        el("savedToast").hidden = false;

        toastTimer = setTimeout(() => {
            el("savedToast").hidden = true;
        }, error ? 7000 : 3500);
    }

    el("closeSavedToast").onclick = () => {
        clearTimeout(toastTimer);
        el("savedToast").hidden = true;
    };

    function escapeHTML(value) {
        return String(value ?? "").replace(/[&<>"']/g, character => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        }[character]));
    }

    function parseDate(value) {
        if (!value) return null;

        let text = String(value).trim();

        // Support MySQL date strings as well as ISO/RFC dates.
        if (/^\d{4}-\d{2}-\d{2} /.test(text)) {
            text = text.replace(" ", "T");
        }

        const date = new Date(text);
        return Number.isNaN(date.getTime()) ? null : date;
    }

    function dayKey(date) {
        if (!date) return "";

        return [
            date.getFullYear(),
            String(date.getMonth() + 1).padStart(2, "0"),
            String(date.getDate()).padStart(2, "0")
        ].join("-");
    }

    function displayDate(date) {
        return date
            ? date.toLocaleDateString("en-GB", {
                day: "2-digit",
                month: "short",
                year: "numeric"
            })
            : "Date unavailable";
    }

   function normalizeDocument(doc) {

    const content =
        String(doc.content ?? "");

    const date =
        parseDate(doc.created_at);

    const suppliedCount =
        Number(doc.word_count);

    const rawSource =
        String(doc.source_type || "ai")
            .trim()
            .toLowerCase();

    const source =
        rawSource === "humanized"
            ? "humanized"
            : "ai";

    return {
        id: String(doc.id),

        topic: String(
            doc.topic || "Untitled Document"
        ),

        content,

        type: String(
            doc.content_type || "Document"
        ),

        source,

        sourceLabel:
            source === "humanized"
                ? "Humanized Content"
                : "AI Content",

        words:
            Number.isFinite(suppliedCount)
            && suppliedCount >= 0
                ? suppliedCount
                : (
                    content.trim()
                        ? content.trim().split(/\s+/).length
                        : 0
                ),

        date,

        day: dayKey(date)
    };
}
    async function api(url, method = "GET") {
        const headers = { Accept: "application/json" };
        const csrf = el("savedCsrfToken")?.value;

        if (csrf && method !== "GET") {
            headers["X-CSRFToken"] = csrf;
        }

        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 30000);

        try {
            const response = await fetch(url, {
                method,
                headers,
                credentials: "same-origin",
                cache: "no-store",
                signal: controller.signal
            });

            if (response.redirected || response.status === 401) {
                throw new Error("Your session has expired. Please sign in again.");
            }

            if (!(response.headers.get("content-type") || "").includes("json")) {
                throw new Error(
                    "The server returned an unexpected response. Please try again."
                );
            }

            const result = await response.json();

            if (!response.ok || result.success !== true) {
                throw new Error(result.message || "Unable to complete this request.");
            }

            return result;
        } catch (error) {
            if (error.name === "AbortError") {
                throw new Error(
                    "The request timed out. Refresh the list before trying again."
                );
            }

            throw error;
        } finally {
            clearTimeout(timeout);
        }
    }

    function state(title, message, icon = "fa-folder-open") {
        list.innerHTML = `
            <div class="saved-state">
                <i class="fas ${icon}" aria-hidden="true"></i>
                <h3>${escapeHTML(title)}</h3>
                <p>${escapeHTML(message)}</p>
            </div>
        `;
    }

    function card(doc) {
        const cleanPreview = doc.content.replace(/\s+/g, " ").trim();
        const excerpt = cleanPreview.length > 260
            ? cleanPreview.slice(0, 260) + "…"
            : cleanPreview;

        return `
            <article class="saved-card" data-id="${escapeHTML(doc.id)}">
                <div class="saved-card-header">
                    <div class="saved-card-title">
                        <div class="saved-file-icon">
                            <i class="fas fa-file-lines" aria-hidden="true"></i>
                        </div>

                        <div>
                            <h3>${escapeHTML(doc.topic)}</h3>
                            <span class="saved-card-type">
                                ${escapeHTML(doc.type)}
                            </span>
                        </div>
                    </div>

                    <span
    class="saved-source-badge saved-source-${escapeHTML(doc.source)}"
>
    <i class="${
        doc.source === "humanized"
            ? "fas fa-user-pen"
            : "fas fa-robot"
    }" aria-hidden="true"></i>

    ${escapeHTML(doc.sourceLabel)}
</span>
                </div>

                <div class="saved-card-meta">
                    <span>
                        <i class="fas fa-align-left" aria-hidden="true"></i>
                        ${doc.words.toLocaleString()} words
                    </span>

                    <span>
                        <i class="far fa-calendar" aria-hidden="true"></i>
                        ${escapeHTML(displayDate(doc.date))}
                    </span>
                </div>

                <p class="saved-card-preview">
                    ${escapeHTML(excerpt || "No content available.")}
                </p>

                <div class="saved-card-actions">
                    <button type="button" class="sd-view" data-action="view">
                        <i class="fas fa-eye" aria-hidden="true"></i>
                        View
                    </button>

                    <button type="button" class="sd-copy" data-action="copy">
                        <i class="fas fa-copy" aria-hidden="true"></i>
                        Copy
                    </button>

                    <button type="button" class="sd-export" data-action="export">
                        <i class="fas fa-file-arrow-down" aria-hidden="true"></i>
                        TXT
                    </button>

                    <button type="button" class="sd-remove" data-action="remove">
                        <i class="fas fa-trash-can" aria-hidden="true"></i>
                        Remove
                    </button>
                </div>
            </article>
        `;
    }

    function renderPagination(totalPages) {
        const container = el("savedPagination");
        container.replaceChildren();
        container.hidden = totalPages <= 1;

        if (totalPages <= 1) return;

        function addButton(label, target, disabled = false, active = false) {
            const button = document.createElement("button");

            button.type = "button";
            button.textContent = label;
            button.disabled = disabled;

            if (active) {
                button.setAttribute("aria-current", "page");
            }

            button.onclick = () => {
                currentPage = target;
                render();

                list.scrollIntoView({
                    block: "start",
                    behavior: "auto"
                });

                container.querySelector('[aria-current="page"]')?.focus({
                    preventScroll: true
                });
            };

            container.appendChild(button);
        }

        addButton("Previous", currentPage - 1, currentPage === 1);

        const start = Math.max(
            1,
            Math.min(currentPage - 2, totalPages - 4)
        );

        const end = Math.min(totalPages, start + 4);

        if (start > 1) {
            addButton("1", 1);

            if (start > 2) {
                const dots = document.createElement("span");
                dots.textContent = "…";
                container.appendChild(dots);
            }
        }

        for (let number = start; number <= end; number++) {
            addButton(String(number), number, false, number === currentPage);
        }

        if (end < totalPages) {
            if (end < totalPages - 1) {
                const dots = document.createElement("span");
                dots.textContent = "…";
                container.appendChild(dots);
            }

            addButton(String(totalPages), totalPages);
        }

        addButton("Next", currentPage + 1, currentPage === totalPages);
    }

    function render() {
        el("savedPagination").hidden = true;

        if (loading) {
            el("savedResults").textContent = "";
            state(
                "Loading your library",
                "Your saved documents will appear shortly.",
                "fa-spinner fa-spin"
            );
            return;
        }

        if (loadError) {
            el("savedTotal").textContent = "Library unavailable";
            el("savedResults").textContent = "";
            state("Unable to load documents", loadError, "fa-circle-exclamation");
            return;
        }

        el("savedTotal").textContent =
            `${documents.length} saved document${documents.length === 1 ? "" : "s"}`;

        const query = el("searchSaved").value.trim().toLowerCase();
        const type = el("savedFilter").value;
        const from = el("savedFrom").value;
        const until = el("savedTo").value;
        const invalidRange = Boolean(from && until && from > until);

        el("savedFilterError").hidden = !invalidRange;

        if (invalidRange) {
            el("savedResults").textContent = "";
            state("Check your date range", "Choose an end date after the start date.");
            return;
        }

        const filtered = documents.filter(doc => {
            const matchesSearch =
                !query ||
                doc.topic.toLowerCase().includes(query) ||
                doc.content.toLowerCase().includes(query);

            const matchesType = !type || doc.type === type;

            const matchesDate =
                (!from || (doc.day && doc.day >= from)) &&
                (!until || (doc.day && doc.day <= until));

            return matchesSearch && matchesType && matchesDate;
        });

        const sort = el("savedSort").value;

        filtered.sort((a, b) => {
            if (sort === "title") {
                return a.topic.localeCompare(b.topic, "en", {
                    sensitivity: "base"
                });
            }

            // Keep records with missing dates at the end.
            if (!a.date && !b.date) return 0;
            if (!a.date) return 1;
            if (!b.date) return -1;

            return sort === "oldest"
                ? a.date.getTime() - b.date.getTime()
                : b.date.getTime() - a.date.getTime();
        });

        const pageSize = Number(el("savedPageSize").value);
        const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));

        currentPage = Math.max(1, Math.min(currentPage, totalPages));

        if (!filtered.length) {
            el("savedResults").textContent = "0 documents";

            state(
                documents.length ? "No matching documents" : "Your library is empty",
                documents.length
                    ? "Try another search or clear your filters."
                    : "Save content from the generator to find it here."
            );

            return;
        }

        const start = (currentPage - 1) * pageSize;
        const visible = filtered.slice(start, start + pageSize);

        list.innerHTML = visible.map(card).join("");

        el("savedResults").textContent =
            `Showing ${start + 1}–${start + visible.length} of ${filtered.length}` +
            ` · Page ${currentPage} of ${totalPages}`;

        renderPagination(totalPages);
    }

    async function loadDocuments() {
        if (loading || deleting) return;

        loading = true;
        loadError = "";
        list.setAttribute("aria-busy", "true");
        el("refreshSaved").disabled = true;

        render();

        try {
            const result = await api(LIST_URL);

            if (!Array.isArray(result.data)) {
                throw new Error("The server returned an invalid document list.");
            }

            documents = result.data.map(normalizeDocument);

            // Include types already present in the database.
            const types = new Set(
                Array.from(el("savedFilter").options, option => option.value)
            );

            for (const doc of documents) {
                if (!types.has(doc.type)) {
                    el("savedFilter").add(new Option(doc.type, doc.type));
                    types.add(doc.type);
                }
            }
        } catch (error) {
            loadError = error.message || "Please use Refresh to try again.";
        } finally {
            loading = false;
            list.setAttribute("aria-busy", "false");
            el("refreshSaved").disabled = false;
            render();
        }
    }

    function openPreview(doc) {
        el("savedModalTitle").textContent = doc.topic;
el("savedModalMeta").textContent =
    `${doc.sourceLabel} · ${doc.type} · ` +
    `${doc.words.toLocaleString()} words · ` +
    displayDate(doc.date);

        // Render stored content as text, not executable HTML.
        el("savedModalContent").textContent =
            doc.content || "No content available.";

        preview.showModal();
    }

    el("closeSavedPreview").onclick = () => preview.close();
    el("closeSavedPreviewBottom").onclick = () => preview.close();

    function exportText(doc) {
        if (!doc.content.trim()) {
            notify("This document has no content to export.", true);
            return;
        }

        const blob = new Blob([doc.content], {
            type: "text/plain;charset=utf-8"
        });

        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");

        const filename = doc.topic
            .replace(/[<>:"/\\|?*\u0000-\u001f]/g, "_")
            .slice(0, 100)
            .replace(/[. ]+$/g, "")
            .trim() || "Saved-Document";

        link.href = url;
        link.download = `${filename}.txt`;

        document.body.appendChild(link);
        link.click();
        link.remove();

        setTimeout(() => URL.revokeObjectURL(url), 10000);
    }

    list.addEventListener("click", async event => {
        const button = event.target.closest("button[data-action]");
        if (!button || deleting) return;

        const cardElement = button.closest(".saved-card");
        const doc = documents.find(item => item.id === cardElement?.dataset.id);

        if (!doc) return;

        const action = button.dataset.action;

        if (action === "view") {
            openPreview(doc);
        }

        if (action === "export") {
            exportText(doc);
        }

        if (action === "copy") {
            if (!doc.content.trim()) {
                notify("This document has no content to copy.", true);
                return;
            }

            button.disabled = true;

            try {
                await navigator.clipboard.writeText(doc.content);
                notify("Document copied to clipboard.");
            } catch {
                notify(
                    "Clipboard access is unavailable. Open the preview and copy the text manually.",
                    true
                );
            } finally {
                button.disabled = false;
            }
        }

        if (action === "remove" && !confirmation.open) {
            pendingDocument = doc;

            el("savedConfirmText").textContent =
                `Remove “${doc.topic}” from your saved documents?`;

            confirmation.showModal();
        }
    });

    el("cancelSavedRemove").onclick = () => {
        if (!deleting) confirmation.close();
    };

    confirmation.addEventListener("cancel", event => {
        if (deleting) event.preventDefault();
    });

    confirmation.addEventListener("close", () => {
        pendingDocument = null;
    });

    el("confirmSavedRemove").onclick = async () => {
        if (!pendingDocument || deleting) return;

        const doc = pendingDocument;
        const button = el("confirmSavedRemove");

        deleting = true;
        button.disabled = true;
        button.textContent = "Removing…";
        el("cancelSavedRemove").disabled = true;
        el("refreshSaved").disabled = true;

        let removed = false;
        let errorMessage = "";

        try {
            await api(REMOVE_URL(doc.id), "POST");

            documents = documents.filter(item => item.id !== doc.id);
            removed = true;
        } catch (error) {
            errorMessage = error.message || "Unable to remove this document.";
        } finally {
            deleting = false;
            button.disabled = false;
            button.textContent = "Remove Document";
            el("cancelSavedRemove").disabled = false;
            el("refreshSaved").disabled = false;

            confirmation.close();
        }

        if (removed) {
            render();

            // Focus remains usable if the last card on a page was removed.
            el("refreshSaved").focus({ preventScroll: true });

            notify("Document removed from your saved library.");
        } else {
            notify(errorMessage, true);
        }
    };

    function resetPage() {
        currentPage = 1;
        render();
    }

    el("searchSaved").addEventListener("input", resetPage);

    [
        "savedFilter",
        "savedFrom",
        "savedTo",
        "savedSort",
        "savedPageSize"
    ].forEach(id => {
        el(id).addEventListener("change", resetPage);
    });

    el("clearSavedFilters").onclick = () => {
        el("searchSaved").value = "";
        el("savedFilter").value = "";
        el("savedFrom").value = "";
        el("savedTo").value = "";
        el("savedSort").value = "newest";

        resetPage();
    };

    el("refreshSaved").onclick = loadDocuments;

    loadDocuments();
});