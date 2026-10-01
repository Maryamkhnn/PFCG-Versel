(() => {
    "use strict";

    const $ = id => document.getElementById(id);
    const pageSize = 6;

    let allItems = [];
    let visibleItems = [];
    let page = 1;
    let lastFocus = null;

    function sourceOf(item) {
        const source = String(
            item.source_type || item.saved_source || "original"
        ).toLowerCase();

        return ["original", "edited", "humanized"].includes(source)
            ? source
            : "original";
    }

    function textOf(value) {
        return String(value || "")
            .replace(/<[^>]*>/g, " ")
            .replace(/\s+/g, " ")
            .trim();
    }

    function dateOf(value) {
        const match = String(value || "")
            .match(/^(\d{4})-(\d{2})-(\d{2})/);

        return match ? match[0] : "";
    }

    function displayDate(value) {
        const date = dateOf(value);

        if (!date) return "Unknown date";

        const [year, month, day] = date.split("-").map(Number);

        return new Date(year, month - 1, day)
            .toLocaleDateString("en-GB", {
                day: "2-digit",
                month: "short",
                year: "numeric"
            });
    }

    function node(tag, className, value) {
        const result = document.createElement(tag);

        if (className) result.className = className;
        if (value !== undefined) result.textContent = value;

        return result;
    }

    function button(label, icon, className, handler) {
        const result = node("button", className);
        result.type = "button";

        const symbol = node("i", "fas " + icon);
        symbol.setAttribute("aria-hidden", "true");

        result.append(
            symbol,
            document.createTextNode(" " + label)
        );

        result.addEventListener("click", () => handler(result));

        return result;
    }

    function notify(message, error = false) {
        const notice = node(
            "div",
            "my-content-notice",
            message
        );

        Object.assign(notice.style, {
            position: "fixed",
            right: "20px",
            bottom: "20px",
            zIndex: "10000",
            maxWidth: "380px",
            padding: "14px 18px",
            borderRadius: "10px",
            color: "#fff",
            background: error ? "#b42340" : "#5b35b5",
            boxShadow: "0 8px 24px #21134444"
        });

        document.body.append(notice);
        setTimeout(() => notice.remove(), 4500);
    }

    async function api(url, payload) {
        const headers = {
            "Content-Type": "application/json"
        };

        const csrf = document.querySelector(
            'meta[name="csrf-token"]'
        )?.content;

        if (csrf) {
            headers["X-CSRFToken"] = csrf;
        }

        const response = await fetch(url, {
            method: "POST",
            credentials: "same-origin",
            headers,
            body: JSON.stringify(payload || {})
        });

        if (response.redirected || response.status === 401) {
            throw new Error(
                "Your session expired. Please sign in again."
            );
        }

        let result;

        try {
            result = await response.json();
        } catch {
            throw new Error("Unexpected server response.");
        }

        if (!response.ok || !result.success) {
            throw new Error(
                result.message || "Request failed."
            );
        }

        return result;
    }

    function saved(item) {
        return (
            item.is_saved === true ||
            item.is_saved === 1 ||
            ["1", "true"].includes(
                String(item.is_saved || "").toLowerCase()
            )
        );
    }

    function badges(item) {
        const box = node("div", "content-badges");
        const source = sourceOf(item);

        const label = source === "humanized"
            ? "Humanized Content"
            : "AI Content";

        const sourceClass = source === "humanized"
            ? "source-humanized"
            : "source-original";

        box.append(
            node(
                "span",
                "content-source-badge " + sourceClass,
                label
            )
        );

        if (
            source === "edited" ||
            (source === "humanized" && item.is_edited)
        ) {
            box.append(
                node(
                    "span",
                    "content-source-badge source-edited",
                    "Edited"
                )
            );
        }

        if (saved(item)) {
            box.append(
                node(
                    "span",
                    "content-saved-badge",
                    "✓ Saved"
                )
            );
        }

        return box;
    }
  async function loadContent(silent = false) {
    const list = $("contentList");

    list.setAttribute("aria-busy", "true");

    // Normal page load par Loading dikhayen.
    // Delete ke baad refresh mein purane cards screen par rakhen.
    if (!silent) {
        list.replaceChildren(
            node(
                "div",
                "content-empty",
                "Loading your content…"
            )
        );
    }

    try {
        const result = await api("/user/api/my-content");

        if (!Array.isArray(result.data)) {
            throw new Error("Invalid content list.");
        }

        allItems = result.data;

        $("contentTotal").textContent =
            allItems.length + " documents";

        // Current page aur search/filter ko preserve karo.
        applyFilters(false);

    } catch (error) {
        if (!silent) {
            list.replaceChildren(
                node(
                    "div",
                    "content-empty",
                    error.message
                )
            );

            $("resultsSummary").textContent =
                "Content could not be loaded.";

            $("contentPagination").hidden = true;
        }

        notify(error.message, true);

    } finally {
        list.setAttribute("aria-busy", "false");
    }
}

    function applyFilters(resetPage = true) {
        if (resetPage) page = 1;

        const search = $("searchContent")
            .value.trim().toLowerCase();

        const type = $("filterType")
            .value.trim().toLowerCase();

        const from = $("dateFrom").value;
        const to = $("dateTo").value;

        const invalid = Boolean(
            from && to && from > to
        );

        $("filterMessage").textContent = invalid
            ? "From Date must be before To Date."
            : "";

        visibleItems = invalid
            ? []
            : allItems.filter(item => {
                const haystack = (
                    String(item.topic || "") +
                    " " +
                    textOf(item.content)
                ).toLowerCase();

                const date = dateOf(item.created_at);

                return (
                    (!search || haystack.includes(search)) &&
                    (!type ||
                        String(item.content_type || "")
                            .toLowerCase() === type) &&
                    (!from || date >= from) &&
                    (!to || date <= to)
                );
            });

        render();
    }

    function openModal(item, clickedButton) {
        $("humanizedSaveBtn")?.remove();

        $("modalTitle").textContent =
            item.topic || "Untitled Content";

        $("modalMeta").textContent =
            (sourceOf(item) === "humanized"
                ? "Humanized Content"
                : "AI Content") +
            " • " +
            (item.content_type || "Content") +
            " • " +
            displayDate(item.created_at);

        $("modalContent").textContent =
            item.content || "No content available.";

        lastFocus = clickedButton;

        const modal = $("contentModal");

        modal.style.display = "flex";
        modal.classList.add("show");
        modal.setAttribute("aria-hidden", "false");

        document.body.classList.add("modal-open");

        $("closeModalBtn").focus();
    }

    function closeModal() {
        const modal = $("contentModal");

        modal.style.display = "none";
        modal.classList.remove("show");
        modal.setAttribute("aria-hidden", "true");

        document.body.classList.remove("modal-open");

        $("humanizedSaveBtn")?.remove();

        if (lastFocus?.isConnected) {
            lastFocus.focus();
        }
    }

    function editHumanized(item, clickedButton) {
        openModal(item, clickedButton);

        const textarea = node(
            "textarea",
            "humanized-edit-textarea"
        );

        textarea.value = String(item.content || "");

        textarea.setAttribute(
            "aria-label",
            "Edit humanized content"
        );

        Object.assign(textarea.style, {
            width: "100%",
            minHeight: "360px",
            padding: "16px",
            resize: "vertical",
            border: "1px solid #d8c6f4",
            borderRadius: "10px",
            font: "inherit",
            lineHeight: "1.7"
        });

        $("modalContent").replaceChildren(textarea);

        const saveButton = button(
            "Save Changes",
            "fa-floppy-disk",
            "edit-btn",
            async () => {
                const updated = textarea.value.trim();

                if (!updated) {
                    notify(
                        "Content cannot be empty.",
                        true
                    );
                    textarea.focus();
                    return;
                }

                saveButton.disabled = true;

                try {
                    await api(
                        "/user/api/humanized-content/" +
                        encodeURIComponent(item.id) +
                        "/edit",
                        { content: updated }
                    );

                    const changed =
                        updated !==
                        String(item.content || "").trim();

                    item.content = updated;
                    item.word_count =
                        updated.split(/\s+/).length;

                    if (changed) {
                        item.is_edited = true;
                        item.is_saved = false;
                    }

                    closeModal();
                    render();

                    notify("Humanized content updated.");

                } catch (error) {
                    notify(error.message, true);

                } finally {
                    saveButton.disabled = false;
                }
            }
        );

        saveButton.id = "humanizedSaveBtn";

        $("contentModal")
            .querySelector(".content-modal-footer")
            .prepend(saveButton);

        textarea.focus();
    }

    function download(blob, title, extension) {
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");

        link.href = url;

        link.download = (
            String(title || "Content")
                .replace(/[<>:"/\\|?*\x00-\x1f]/g, "_")
                .slice(0, 80) ||
            "Content"
        ) + "." + extension;

        document.body.append(link);

        link.click();
        link.remove();

        setTimeout(
            () => URL.revokeObjectURL(url),
            1000
        );
    }

    function printPdf(item) {
        const win = window.open("", "_blank");

        if (!win) {
            notify(
                "Allow pop-ups for PDF export.",
                true
            );
            return;
        }

        const escape = value => String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");

        win.document.write(
            "<!doctype html>" +
            "<html><head><meta charset='utf-8'>" +
            "<title>" +
            escape(item.topic || "Content") +
            "</title>" +
            "<style>" +
            "body{font-family:Arial,sans-serif;" +
            "margin:35px;line-height:1.6}" +
            "main{white-space:pre-wrap;" +
            "overflow-wrap:anywhere}" +
            "@media print{body{margin:15mm}}" +
            "</style></head><body>" +
            "<h1>" +
            escape(item.topic || "Content") +
            "</h1><main>" +
            escape(item.content) +
            "</main></body></html>"
        );

        win.document.close();

        setTimeout(() => {
            win.focus();
            win.print();
        }, 250);
    }

    function confirmDelete(item) {
        const modal = $("deleteConfirmModal");
        const cancel = $("cancelDeleteBtn");
        const confirm = $("confirmDeleteBtn");

        if (!modal || !cancel || !confirm) {
            return Promise.resolve(
                window.confirm("Delete this content?")
            );
        }

        $("deleteConfirmDescription").textContent =
            sourceOf(item) === "edited"
                ? "Delete this edited content? Check whether your server also removes its AI original."
                : "This content will be permanently deleted. This action cannot be undone.";

        modal.hidden = false;

        return new Promise(resolve => {
            function finish(value) {
                modal.hidden = true;

                cancel.removeEventListener(
                    "click",
                    onCancel
                );

                confirm.removeEventListener(
                    "click",
                    onConfirm
                );

                modal.removeEventListener(
                    "click",
                    onOverlay
                );

                document.removeEventListener(
                    "keydown",
                    onKey
                );

                resolve(value);
            }

            const onCancel = () => finish(false);
            const onConfirm = () => finish(true);

            const onOverlay = event => {
                if (event.target === modal) {
                    finish(false);
                }
            };

            const onKey = event => {
                if (event.key === "Escape") {
                    finish(false);
                }
            };

            cancel.addEventListener(
                "click",
                onCancel
            );

            confirm.addEventListener(
                "click",
                onConfirm
            );

            modal.addEventListener(
                "click",
                onOverlay
            );

            document.addEventListener(
                "keydown",
                onKey
            );

            cancel.focus();
        });
    }
async function deleteItem(item, clickedButton) {
    const confirmed = await confirmDelete(item);

    if (!confirmed) return;

    const originalLabel = clickedButton.innerHTML;

    clickedButton.disabled = true;
    clickedButton.textContent = "Deleting…";

    const source = sourceOf(item);

    const id = source === "humanized"
        ? item.id
        : (item.original_content_id || item.id);

    try {
        await api(
            "/user/api/delete-document/" +
            encodeURIComponent(id),
            { source_type: source }
        );

        // Cards ko pehle blank kiye baghair naya data lao.
        await loadContent(true);

        notify("Content deleted.");

    } catch (error) {
        notify(error.message, true);

    } finally {
        clickedButton.disabled = false;
        clickedButton.innerHTML = originalLabel;
    }
}
    function card(item) {
        const article = node(
            "article",
            "content-card"
        );

        const header = node(
            "div",
            "card-header"
        );

        const icon = node(
            "span",
            "card-document-icon"
        );

        icon.innerHTML =
            '<i class="fas fa-file-lines" aria-hidden="true"></i>';

        const heading = node(
            "div",
            "card-heading"
        );

        heading.append(
            node(
                "h3",
                "",
                item.topic || "Untitled Content"
            )
        );

        const count =
            Number(item.word_count) ||
            textOf(item.content)
                .split(/\s+/)
                .filter(Boolean)
                .length;

        heading.append(
            node(
                "p",
                "",
                (item.content_type || "Content") +
                " • " +
                count +
                " Words • " +
                displayDate(item.created_at)
            )
        );

        header.append(
            icon,
            heading,
            badges(item)
        );

        const preview = textOf(item.content);

        const body = node(
            "div",
            "card-body",
            preview.length > 250
                ? preview.slice(0, 250) + "…"
                : (
                    preview ||
                    "No preview available."
                )
        );

        const actions = node(
            "div",
            "card-actions"
        );

        actions.append(
            button(
                "View",
                "fa-eye",
                "view-btn",
                clicked => openModal(
                    item,
                    clicked
                )
            )
        );

        actions.append(
            button(
                "Copy",
                "fa-copy",
                "copy-btn",
                async () => {
                    try {
                        await navigator.clipboard.writeText(
                            String(item.content || "")
                        );

                        notify("Content copied.");

                    } catch {
                        notify(
                            "Copy failed. Open View to select the text.",
                            true
                        );
                    }
                }
            )
        );
actions.append(
    button("Edit", "fa-pen", "edit-btn", () => {
        const humanized = sourceOf(item) === "humanized";

        const params = new URLSearchParams({
            id: String(
                humanized
                    ? item.id
                    : (item.original_content_id || item.id)
            )
        });

        if (humanized) {
            params.set("source", "humanized");
        }

        window.location.href =
            "/user/edit-content?" + params.toString();
    })
);

        const exportBox = node(
            "div",
            "card-export-wrap"
        );

        const menu = node(
            "div",
            "card-export-menu"
        );

        menu.hidden = true;

        const exportButton = button(
            "Export",
            "fa-download",
            "export-btn",
            () => {
                menu.hidden = !menu.hidden;

                exportButton.setAttribute(
                    "aria-expanded",
                    String(!menu.hidden)
                );
            }
        );

        exportButton.setAttribute(
            "aria-expanded",
            "false"
        );

        menu.append(
            button(
                "TXT",
                "fa-file-lines",
                "",
                () => {
                    menu.hidden = true;

                    download(
                        new Blob(
                            [
                                String(
                                    item.content || ""
                                )
                            ],
                            {
                                type:
                                    "text/plain;charset=utf-8"
                            }
                        ),
                        item.topic,
                        "txt"
                    );
                }
            ),

            button(
                "PDF",
                "fa-file-pdf",
                "",
                () => {
                    menu.hidden = true;
                    printPdf(item);
                }
            )
        );

        exportBox.append(
            exportButton,
            menu
        );

        actions.append(exportBox);

        actions.append(
            button(
                "Delete",
                "fa-trash",
                "delete-btn",
                clicked => deleteItem(
                    item,
                    clicked
                )
            )
        );

        article.append(
            header,
            body,
            actions
        );

        return article;
    }

    function render() {
        const list = $("contentList");
        const total = visibleItems.length;

        const pages = Math.max(
            1,
            Math.ceil(total / pageSize)
        );

        page = Math.max(
            1,
            Math.min(page, pages)
        );

        const start =
            (page - 1) * pageSize;

        const end = Math.min(
            start + pageSize,
            total
        );

        $("resultsSummary").textContent =
            total
                ? "Showing " +
                  (start + 1) +
                  "–" +
                  end +
                  " of " +
                  total +
                  " results"
                : "0 results";

        list.replaceChildren();

        if (!total) {
            list.append(
                node(
                    "div",
                    "content-empty",
                    allItems.length
                        ? "No content matches your filters."
                        : "No content found."
                )
            );

        } else {
            visibleItems
                .slice(start, end)
                .forEach(item => {
                    list.append(card(item));
                });
        }

        $("contentPagination").hidden =
            total === 0;

        $("pageInfo").textContent =
            "Page " +
            page +
            " of " +
            pages;

        $("previousPage").disabled =
            page === 1;

        $("nextPage").disabled =
            page === pages;
    }

    document.addEventListener(
        "DOMContentLoaded",
        () => {
            const required = [
                "contentList",
                "contentTotal",
                "searchContent",
                "filterType",
                "dateFrom",
                "dateTo",
                "filterMessage",
                "resultsSummary",
                "contentPagination",
                "pageInfo",
                "previousPage",
                "nextPage",
                "resetFilters",
                "contentModal",
                "modalTitle",
                "modalMeta",
                "modalContent",
                "closeModalBtn",
                "modalCloseBottomBtn"
            ];

            if (
                required.some(id => !$(id))
            ) {
                console.error(
                    "My Content template is missing required elements."
                );

                return;
            }

            [
                "searchContent",
                "dateFrom",
                "dateTo"
            ].forEach(id => {
                $(id).addEventListener(
                    "input",
                    () => applyFilters()
                );
            });

            $("filterType")
                .addEventListener(
                    "change",
                    () => applyFilters()
                );

            $("resetFilters")
                .addEventListener(
                    "click",
                    () => {
                        [
                            "searchContent",
                            "dateFrom",
                            "dateTo",
                            "filterType"
                        ].forEach(id => {
                            $(id).value = "";
                        });

                        applyFilters();
                    }
                );

            $("previousPage")
                .addEventListener(
                    "click",
                    () => {
                        if (page > 1) {
                            page--;
                            render();
                        }
                    }
                );

            $("nextPage")
                .addEventListener(
                    "click",
                    () => {
                        if (
                            page * pageSize <
                            visibleItems.length
                        ) {
                            page++;
                            render();
                        }
                    }
                );

            $("closeModalBtn")
                .addEventListener(
                    "click",
                    closeModal
                );

            $("modalCloseBottomBtn")
                .addEventListener(
                    "click",
                    closeModal
                );

            $("contentModal")
                .addEventListener(
                    "click",
                    event => {
                        if (
                            event.target ===
                            $("contentModal")
                        ) {
                            closeModal();
                        }
                    }
                );

            document.addEventListener(
                "keydown",
                event => {
                    if (
                        event.key === "Escape" &&
                        $("contentModal")
                            .classList.contains(
                                "show"
                            )
                    ) {
                        closeModal();
                    }
                }
            );

            loadContent();
        }
    );
})();