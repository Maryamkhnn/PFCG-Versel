document.addEventListener("DOMContentLoaded", () => {

   const el = id => document.getElementById(id);

function requiredEl(id) {

    const node = document.getElementById(id);

    if (!node) {
        console.error(
            `EDITOR ERROR: HTML element #${id} was not found.`
        );
    }

    return node;
}
    let toastTimer;

    function notice(message, error = false) {
        el("noticeText").textContent = message;
        el("editorNotice").classList.toggle("error", error);
        el("editorNotice").hidden = false;

        clearTimeout(toastTimer);

        toastTimer = setTimeout(() => {
            el("editorNotice").hidden = true;
        }, error ? 8000 : 4000);
    }

    el("closeNotice").onclick = () => {
        el("editorNotice").hidden = true;
    };

    if (!window.Quill) {
        notice("Editor could not load. Please reload the page.", true);
        return;
    }

    const Parchment = Quill.import("parchment");

    Quill.register(
        new Parchment.StyleAttributor(
            "lineheight",
            "line-height",
            {
                scope: Parchment.Scope.BLOCK,
                whitelist: ["1", "1.5", "2", "2.5"]
            }
        ),
        true
    );

    const Delta = Quill.import("delta");

    const formats = [
        "header", "font", "size",
        "bold", "italic", "underline", "strike",
        "color", "background",
        "align", "list", "indent", "lineheight"
    ];

    const editor = new Quill("#editorContent", {
        theme: "snow",
        readOnly: true,
        formats,
        placeholder: "Open a document to begin writing...",
        modules: {
            toolbar: "#editorToolbar",
            history: {
                delay: 700,
                maxStack: 100,
                userOnly: false
            }
        }
    });

    const preview = new Quill("#previewContent", {
        theme: "snow",
        readOnly: true,
        formats,
        modules: { toolbar: false }
    });

    const api = "/user/api/edit-content";

    let id = null;
    let revision = "";
    let baseline = "";
    let savedDelta = null;

    let loading = false;
    let saving = null;
    let paused = false;
    let timer;

    let range = { index: 0, length: 0 };
    let findPosition = 0;
    let proposal = null;
    let aiBusy = false;
    let historyCursor = null;
    let historyTicket = 0;

    const snapshot = () => JSON.stringify(editor.getContents());
    const plain = () => editor.getText().slice(0, -1);

    const dirty = () => {
        return id !== null && snapshot() !== baseline;
    };

    async function request(path, data, blob = false) {

        const headers = data === undefined
            ? {}
            : { "Content-Type": "application/json" };

        const csrf = document.querySelector(
            'meta[name="csrf-token"]'
        )?.content;

        if (csrf) {
            headers["X-CSRFToken"] = csrf;
        }

        const response = await fetch(api + path, {
            method: data === undefined ? "GET" : "POST",
            credentials: "same-origin",
            headers,
            body: data === undefined
                ? undefined
                : JSON.stringify(data)
        });

        if (response.redirected || response.status === 401) {
            throw new Error(
                "Your session expired. Please log in again."
            );
        }

        if (blob && response.ok) {
            return response.blob();
        }

        let result;

        try {
            result = await response.json();
        } catch {
            throw new Error(
                "Unexpected server response. Please try again."
            );
        }

        if (!response.ok || !result.success) {
            throw new Error(
                result.message || "Unable to complete request."
            );
        }

        return result;
    }

    /* STATISTICS, STATUS AND OUTLINE */

    function refresh() {
        const text = plain();

        const words = text.trim()
            ? text.trim().split(/\s+/).length
            : 0;

        el("wordCount").textContent = words;
        el("characterCount").textContent = Array.from(text).length;

        el("paragraphCount").textContent = text
            .split("\n")
            .filter(paragraph => paragraph.trim())
            .length;

        el("readingTime").textContent = words
            ? Math.ceil(words / 200) + " min"
            : "0 min";

        el("saveStatusBadge").textContent = !id
            ? "No document selected"
            : saving
                ? "Saving..."
                : paused
                    ? "Auto-save paused"
                    : dirty()
                        ? "Unsaved changes"
                        : "All changes saved";

        el("editingControls").disabled = !id || loading;
        editor.enable(Boolean(id) && !loading);

        el("saveBtn").disabled =
            !id || loading || Boolean(saving) || !dirty();

        el("loadDocumentBtn").disabled = loading || Boolean(saving);
        el("documentSelector").disabled = loading || Boolean(saving);
        el("backToContentBtn").disabled = loading || Boolean(saving);

        el("resetBtn").disabled =
            loading || Boolean(saving) || !dirty();

        el("assistBtn").disabled = !id || loading || aiBusy;
        const refreshHistoryButton = el("refreshHistoryBtn");

if (refreshHistoryButton) {
    refreshHistoryButton.disabled = !id || loading;
}

    
const outlineList = el("outlineList");

if (outlineList && !outlineList.children.length) {
    outlineList.textContent =
        "Add headings to create an outline.";
}
    }

    /* AUTO-SAVE */

    function schedule() {
        clearTimeout(timer);

        if (
            id &&
            dirty() &&
            el("autoSave").checked &&
            !paused &&
            !loading &&
            !saving &&
            !el("confirmModal").open
        ) {
            timer = setTimeout(() => save(true), 2500);
        }
    }

   async function save(automatic = false) {
    clearTimeout(timer);

    if (saving) return saving;
    if (!id || loading || !dirty()) return;

    const content = plain();

    if (!content.trim()) {
        paused = true;
        refresh();
        notice("Content cannot be empty. Auto-save paused.", true);
        return;
    }

    const captured = JSON.parse(snapshot());
    const capturedKey = JSON.stringify(captured);
    const capturedId = id;
    const isHumanized =
        new URLSearchParams(location.search).get("source") === "humanized";

    saving = (async () => {
        try {
            if (isHumanized) {
                const csrf = document.querySelector(
                    'meta[name="csrf-token"]'
                )?.content;

                const response = await fetch(
                    "/user/api/humanized-content/" +
                    encodeURIComponent(capturedId) +
                    "/edit",
                    {
                        method: "POST",
                        credentials: "same-origin",
                        headers: {
                            "Content-Type": "application/json",
                            ...(csrf ? { "X-CSRFToken": csrf } : {})
                        },
                        body: JSON.stringify({ content })
                    }
                );

                const result = await response.json();

                if (!response.ok || !result.success) {
                    throw new Error(
                        result.message || "Unable to save changes."
                    );
                }
            } else {
                const result = await request("/update", {
                    id: capturedId,
                    content,
                    editor_delta: captured,
                    revision,
                    reason: automatic ? "Auto-save" : "Manual save"
                });

                revision = result.revision;
            }

            baseline = capturedKey;
            savedDelta = captured;
            paused = false;

            el("lastSaved").textContent =
                "Saved at " +
                new Date().toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit"
                });

            if (!automatic) {
                notice("Changes saved successfully.");
            }

        } catch (error) {
            paused = true;
            notice(
                error.message + " Your draft is still in the editor.",
                true
            );
        }
    })();

    refresh();
    await saving;
    saving = null;
    refresh();
    schedule();

    if (!isHumanized) {
        loadHistory();
    }
}
    /* UNSAVED CHANGES */

    async function discard(message) {
        clearTimeout(timer);

        if (saving) await saving;

        clearTimeout(timer);

        if (!dirty()) return true;

        const dialog = el("confirmModal");

        if (dialog.open) return false;

        el("confirmMessage").textContent = message;
        dialog.returnValue = "cancel";

        const accepted = await new Promise(resolve => {
            dialog.addEventListener("close", () => {
                resolve(dialog.returnValue === "discard");
            }, { once: true });

            dialog.showModal();
        });

        if (!accepted) schedule();

        return accepted;
    }

    function install(delta, content = "") {
        editor.setContents(
            delta || { ops: [{ insert: content + "\n" }] },
            "silent"
        );

        editor.history.clear();

        range = { index: 0, length: 0 };
        findPosition = 0;
        proposal = null;

        el("suggestionPanel").hidden = true;

        refresh();
    }
async function requestMyContent() {
    const csrf = document.querySelector(
        'meta[name="csrf-token"]'
    )?.content;

    const response = await fetch("/user/api/my-content", {
        method: "POST",
        credentials: "same-origin",
        headers: {
            "Content-Type": "application/json",
            ...(csrf ? { "X-CSRFToken": csrf } : {})
        },
        body: JSON.stringify({})
    });

    const result = await response.json();

    if (!response.ok || !result.success) {
        throw new Error(
            result.message || "Unable to load humanized content."
        );
    }

    return result;
}
    /* OPEN DOCUMENT */

    async function openDocument(value) {
    if (!value || loading || saving) return;

    if (!await discard(
        "Open another document and discard unsaved changes?"
    )) return;

    loading = true;
    refresh();

    try {
        const isHumanized =
            new URLSearchParams(window.location.search)
                .get("source") === "humanized";

        let data;

        if (isHumanized) {
            const result = await requestMyContent();

            data = (result.data || []).find(item =>
                String(item.id) === String(value) &&
                String(item.source_type).toLowerCase() === "humanized"
            );

            if (!data) {
                throw new Error("Humanized content not found.");
            }
        } else {
            const result = await request("/get", { id: value });
            data = result.data;
        }

        id = data.id;
        revision = data.revision || "";
        paused = false;

        install(
            isHumanized ? null : data.editor_delta,
            data.content || ""
        );

        savedDelta = JSON.parse(snapshot());
        baseline = snapshot();

        el("contentTitle").textContent =
            data.topic || "Humanized Content";

        el("contentType").textContent =
            data.content_type || "Content";

        el("contentDate").textContent =
            String(data.created_at || "").slice(0, 10);

        el("lastSaved").textContent = "Loaded from database";

        const selector = el("documentSelector");
        const optionValue = isHumanized
            ? "humanized:" + id
            : String(id);

        if (![...selector.options].some(
            option => option.value === optionValue
        )) {
            selector.add(new Option(
                data.topic || "Humanized Content",
                optionValue
            ));
        }

        selector.value = optionValue;

        const url = new URL(window.location.href);
        url.searchParams.set("id", id);

        if (isHumanized) {
            url.searchParams.set("source", "humanized");
        }

        history.replaceState({}, "", url);

        if (!isHumanized) {
            loadHistory();
        }

    } catch (error) {
        console.error("EDITOR LOAD ERROR:", error);
        notice(error.message || "Unable to load content.", true);

    } finally {
        loading = false;
        refresh();
        schedule();
    }
}
    /* VERSION HISTORY */
async function loadHistory(older = false) {

    if (!id) return;

    // History UI tumhari current HTML mein optional hai
    const historyList = el("versionList");
    const olderButton = el("olderVersionsBtn");

    // Agar history panel HTML mein nahi hai to quietly return
    if (!historyList) {
        return;
    }

    const capturedId = id;
    const ticket = ++historyTicket;

    try {

        const { data } = await request("/history", {
            id,
            before: older ? historyCursor : null
        });

        if (
            id !== capturedId ||
            ticket !== historyTicket
        ) {
            return;
        }

        if (!older) {
            historyList.replaceChildren();
        }

        for (const item of data.items) {

            const button = document.createElement("button");

            button.type = "button";

            button.textContent =
                `${item.reason} · ` +
                new Date(item.created_at).toLocaleString();

            button.title =
                "Load this version as an unsaved draft";

            button.onclick = async () => {

                if (
                    loading ||
                    saving ||
                    id !== capturedId
                ) {
                    return;
                }

                if (!await discard(
                    "Load this version and discard unsaved changes?"
                )) {
                    return;
                }

                loading = true;
                refresh();

                try {

                    const result = await request("/version", {
                        id,
                        version_id: item.id
                    });

                    const autoSave = el("autoSave");

                    if (autoSave) {
                        autoSave.checked = false;
                    }

                    install(
                        result.data.editor_delta,
                        result.data.content || ""
                    );

                    notice(
                        "Version loaded as a draft. Review it, then Save Changes."
                    );

                } catch (error) {

                    notice(error.message, true);

                } finally {

                    loading = false;
                    refresh();
                    schedule();
                }
            };

            historyList.append(button);
        }

        if (!historyList.children.length) {
            historyList.textContent =
                "History starts with your first save.";
        }

        historyCursor = data.next;

        if (olderButton) {
            olderButton.hidden = !historyCursor;
        }

    } catch (error) {

        if (ticket === historyTicket) {
            historyList.textContent = error.message;
        }
    }
}

    /* EDITOR EVENTS */

    editor.on("text-change", () => {
        findPosition = 0;
        refresh();
        schedule();
    });

    editor.on("selection-change", value => {
        if (value) range = value;
    });

    el("autoSave").onchange = schedule;
    el("saveBtn").onclick = () => save(false);

    el("loadDocumentBtn").onclick = () => {
        if (!el("documentSelector").value) {
            notice("Choose a document first.", true);
            return;
        }

        openDocument(el("documentSelector").value);
    };

    el("undoBtn").onclick = () => editor.history.undo();
    el("redoBtn").onclick = () => editor.history.redo();

    el("lineSpacing").onchange = event => {
        const index = Math.min(
            range.index,
            editor.getLength() - 1
        );

        editor.formatLine(
            index,
            Math.min(range.length, editor.getLength() - index),
            "lineheight",
            event.target.value,
            "user"
        );
    };

    el("resetBtn").onclick = async () => {
        if (await discard(
            "Discard changes and restore the last saved draft?"
        )) {
            install(savedDelta);
            refresh();
        }
    };

    el("backToContentBtn").onclick = async () => {
        if (await discard(
            "Leave this editor and discard unsaved changes?"
        )) {
            baseline = snapshot();
            location.href = el("editorPage").dataset.back;
        }
    };

    /* FOCUS MODE */

    el("focusBtn").onclick = () => {
        const active = el("editorPage")
            .classList.toggle("focus-mode");

        el("focusBtn").textContent =
            active ? "Exit Focus" : "Focus Mode";

        el("focusBtn").setAttribute(
            "aria-pressed",
            String(active)
        );
    };
const refreshHistoryBtn = el("refreshHistoryBtn");

if (refreshHistoryBtn) {
    refreshHistoryBtn.onclick = () => loadHistory();
}


const olderVersionsBtn = el("olderVersionsBtn");

if (olderVersionsBtn) {
    olderVersionsBtn.onclick = () => loadHistory(true);
}
    

    /* COPY / EXPORT */

    el("copyBtn").onclick = async () => {
        try {
            await navigator.clipboard.writeText(plain());
            notice("Content copied.");

        } catch {
            notice(
                "Clipboard unavailable. Select text and press Ctrl+C.",
                true
            );
        }
    };

    function download(blob, extension, title) {
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");

        const name = title
            .replace(/[<>:"/\\|?*\u0000-\u001f]/g, "_")
            .slice(0, 80)
            .replace(/[. ]+$/g, "") || "Document";

        link.href = url;
        link.download = name + "." + extension;

        document.body.append(link);
        link.click();
        link.remove();

        setTimeout(() => URL.revokeObjectURL(url), 1000);
    }

    el("downloadBtn").onclick = () => {
        download(
            new Blob(
                [plain()],
                { type: "text/plain;charset=utf-8" }
            ),
            "txt",
            el("contentTitle").textContent
        );
    };

    for (const [buttonId, format] of [
        ["exportPdfBtn", "pdf"],
        ["exportWordBtn", "docx"]
    ]) {
        el(buttonId).onclick = async () => {
            const button = el(buttonId);
            const originalMarkup = button.innerHTML;
            const title = el("contentTitle").textContent;

            button.disabled = true;
            button.setAttribute("aria-busy", "true");
            button.textContent = "Preparing…";

            try {
                const blob = await request(
                    "/export",
                    {
                        id,
                        format,
                        editor_delta: editor.getContents()
                    },
                    true
                );

                download(blob, format, title);
                notice("Your download has started.");

            } catch (error) {
                notice(
                    error.message ||
                    "Unable to download the document. Please try again.",
                    true
                );

            } finally {
                button.disabled = false;
                button.removeAttribute("aria-busy");
                button.innerHTML = originalMarkup;
            }
        };
    }

    /* PREVIEW */

    el("previewBtn").onclick = () => {
        preview.setContents(editor.getContents(), "silent");

        el("previewTitle").textContent =
            el("contentTitle").textContent;

        el("previewModal").showModal();
    };

    el("closePreviewBtn").onclick = () => {
        el("previewModal").close();
    };

    /* FIND AND REPLACE */

    el("findText").oninput = () => {
        findPosition = 0;
    };

    el("findNextBtn").onclick = () => {
        const term = el("findText").value;

        if (!term) {
            notice("Enter text to find.", true);
            return;
        }

        let index = plain().indexOf(term, findPosition);

        if (index < 0) {
            index = plain().indexOf(term);
        }

        if (index < 0) {
            notice("No matching text found.");
            return;
        }

        editor.setSelection(index, term.length);
        editor.scrollSelectionIntoView();

        findPosition = index + term.length;
    };

    function inline(index) {
        const attributes = editor.getFormat(index, 1);
        const result = {};

        for (const key of [
            "bold", "italic", "underline", "strike",
            "font", "size", "color", "background"
        ]) {
            if (
                attributes[key] !== undefined &&
                !Array.isArray(attributes[key])
            ) {
                result[key] = attributes[key];
            }
        }

        return result;
    }

    el("replaceAllBtn").onclick = () => {
        const term = el("findText").value;
        const replacement = el("replaceText").value;

        if (!term) {
            notice("Enter text to find.", true);
            return;
        }

        const text = plain();

        let changes = new Delta();
        let cursor = 0;
        let count = 0;
        let index = text.indexOf(term);

        while (index >= 0) {
            changes = changes
                .retain(index - cursor)
                .delete(term.length);

            if (replacement) {
                changes = changes.insert(
                    replacement,
                    inline(index)
                );
            }

            cursor = index + term.length;
            count++;
            index = text.indexOf(term, cursor);
        }

        if (!count) {
            notice("No matching text found.");
            return;
        }

        editor.history.cutoff();
        editor.updateContents(changes, "user");
        editor.history.cutoff();

        notice(`${count} occurrence(s) replaced.`);
    };
/* ========================================================
   AI SUGGESTION DIFFERENCE HIGHLIGHT
======================================================== */

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


function tokenizeDifference(text) {
    return String(text).match(
        /\s+|[\p{L}\p{N}’'-]+|[^\s\p{L}\p{N}]/gu
    ) || [];
}


function buildDifference(original, suggested) {

    const before = tokenizeDifference(original);
    const after = tokenizeDifference(suggested);

    /*
       LCS table:
       Finds text shared by both versions so that only
       genuinely changed portions are highlighted.
    */

    const rows = before.length + 1;
    const cols = after.length + 1;

    const table = Array.from(
        { length: rows },
        () => new Uint32Array(cols)
    );

    for (let i = before.length - 1; i >= 0; i--) {

        for (let j = after.length - 1; j >= 0; j--) {

            if (before[i] === after[j]) {

                table[i][j] =
                    table[i + 1][j + 1] + 1;

            } else {

                table[i][j] = Math.max(
                    table[i + 1][j],
                    table[i][j + 1]
                );
            }
        }
    }


    let i = 0;
    let j = 0;

    let originalHtml = "";
    let suggestedHtml = "";

    let changed = false;


    while (
        i < before.length ||
        j < after.length
    ) {

        /*
           Same token
        */

        if (
            i < before.length &&
            j < after.length &&
            before[i] === after[j]
        ) {

            const safe = escapeHtml(before[i]);

            originalHtml += safe;
            suggestedHtml += safe;

            i++;
            j++;

            continue;
        }


        /*
           Text removed/replaced from original
        */

        if (
            i < before.length &&
            (
                j >= after.length ||
                table[i + 1][j] >=
                table[i][j + 1]
            )
        ) {

            changed = true;

            originalHtml +=
                '<mark class="diff-removed">' +
                escapeHtml(before[i]) +
                '</mark>';

            i++;

            continue;
        }


        /*
           New/replacement text from AI
        */

        if (j < after.length) {

            changed = true;

            suggestedHtml +=
                '<mark class="diff-added">' +
                escapeHtml(after[j]) +
                '</mark>';

            j++;
        }
    }


    return {
        originalHtml,
        suggestedHtml,
        changed
    };
}


function showSuggestionDifference(
    original,
    suggested,
    action
) {

    const beforeBox = el("beforeText");
    const afterBox = el("afterText");

    const result = buildDifference(
        original,
        suggested
    );


    /*
       No actual change
    */

    if (!result.changed) {

        beforeBox.textContent = original;

        if (action === "grammar") {

            afterBox.innerHTML = `
                <div class="no-ai-changes">
                    <i class="fas fa-circle-check"></i>

                    <div>
                        <strong>
                            No corrections needed
                        </strong>

                        <span>
                            No grammar, spelling or punctuation
                            errors were found in the selected text.
                        </span>
                    </div>
                </div>
            `;

        } else {

            afterBox.innerHTML = `
                <div class="no-ai-changes">
                    <i class="fas fa-circle-info"></i>

                    <div>
                        <strong>
                            No meaningful changes suggested
                        </strong>

                        <span>
                            Try another writing action or select
                            a different passage.
                        </span>
                    </div>
                </div>
            `;
        }

        return false;
    }


    /*
       Actual differences
    */

    beforeBox.innerHTML =
        result.originalHtml;

    afterBox.innerHTML =
        result.suggestedHtml;

    return true;
}
    /* AI SUGGESTIONS */

    el("assistBtn").onclick = async () => {
        const selected = {
            index: range.index,
            length: Math.min(
                range.length,
                editor.getLength() - 1 - range.index
            )
        };

        if (selected.length < 1 || selected.length > 6000) {
            notice(
                "Select 1–6,000 characters in the editor first.",
                true
            );
            return;
        }

        const capturedId = id;
        const key = snapshot();

        const text = editor.getText(
            selected.index,
            selected.length
        );

        proposal = null;
        el("suggestionPanel").hidden = true;

        aiBusy = true;
        el("assistBtn").textContent = "Preparing suggestion...";

        refresh();

        try {
            const { data } = await request("/assist", {
                id,
                action: el("assistAction").value,
                text
            });

            if (id !== capturedId || snapshot() !== key) {
                notice(
                    "The draft changed. Select text and request a fresh suggestion."
                );
                return;
            }

           const action = el("assistAction").value;

const hasChanges = showSuggestionDifference(
    text,
    data.text,
    action
);

if (hasChanges) {

    proposal = {
        ...selected,
        key,
        text: data.text
    };

    el("acceptSuggestionBtn").disabled = false;

} else {

    /*
       Nothing to apply when AI returned
       exactly the same text.
    */

    proposal = null;

    el("acceptSuggestionBtn").disabled = true;
}

el("suggestionPanel").hidden = false;

        } catch (error) {
            notice(error.message, true);

        } finally {
            aiBusy = false;
            el("assistBtn").textContent = "Get Suggestion";
            refresh();
        }
    };

    el("acceptSuggestionBtn").onclick = () => {
        if (!proposal) return;

        if (snapshot() !== proposal.key) {
            notice(
                "The draft changed. Request a fresh suggestion.",
                true
            );
            return;
        }

        const changes = new Delta()
            .retain(proposal.index)
            .delete(proposal.length)
            .insert(proposal.text, inline(proposal.index));

        editor.history.cutoff();
        editor.updateContents(changes, "user");
        editor.history.cutoff();

        proposal = null;
        el("suggestionPanel").hidden = true;

        notice("Suggestion applied.");
    };

    el("rejectSuggestionBtn").onclick = () => {
        proposal = null;
        el("suggestionPanel").hidden = true;
    };

    /* SHORTCUTS AND LEAVING PROTECTION */

    document.addEventListener("keydown", event => {
        if (
            (event.ctrlKey || event.metaKey) &&
            event.key.toLowerCase() === "s"
        ) {
            event.preventDefault();
            save(false);
        }

        if (
            event.key === "Escape" &&
            !el("previewModal").open &&
            !el("confirmModal").open
        ) {
            el("editorPage").classList.remove("focus-mode");
            el("focusBtn").textContent = "Focus Mode";
            el("focusBtn").setAttribute("aria-pressed", "false");
        }
    });

    window.addEventListener("beforeunload", event => {
        if (dirty() || saving) {
            event.preventDefault();
            event.returnValue = "";
        }
    });

    /* INITIALIZE */

   /* ========================================================
   INITIALIZE
======================================================== */

(async function initializeEditor() {
    try {
        const selector = el("documentSelector");
        selector.replaceChildren(
            new Option("Choose a document...", "")
        );

        const params = new URLSearchParams(window.location.search);
        const selectedId = params.get("id");
        const isHumanized = params.get("source") === "humanized";

        // URL se document aaya hai to pehle wahi khol do.
        // Dropdown ki request ka wait karne ki zaroorat nahi.
        if (selectedId) {
            if (isHumanized) {
                selector.add(new Option(
                    "Humanized Content",
                    "humanized:" + selectedId
                ));
                selector.value = "humanized:" + selectedId;
            } else {
                selector.add(new Option(
                    "Loading document...",
                    String(selectedId)
                ));
                selector.value = String(selectedId);
            }

            await openDocument(String(selectedId));
            return;
        }

        // Sirf jab Editor seedha khola jaye tab dropdown load karo.
        loading = true;
        refresh();

        const result = await request("");

        if (Array.isArray(result.data)) {
            result.data.forEach(item => {
                selector.add(new Option(
                    item.topic || "Untitled Content",
                    String(item.id)
                ));
            });
        }

    } catch (error) {
        console.error("EDITOR INITIALIZATION ERROR:", error);
        notice(
            error.message || "Unable to load content.",
            true
        );
    } finally {
        loading = false;
        refresh();
    }
})();
});
