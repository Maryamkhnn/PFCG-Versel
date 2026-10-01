/* =====================================================
   PFCG AI — GENERATOR
===================================================== */

const generateBtn = document.getElementById("generateBtn");
const regenerateBtn = document.getElementById("regenerateBtn");
const humanizeBtn = document.getElementById("humanizeBtn");

const plagiarismBtn = document.getElementById("plagiarismBtn");
const humanizedPlagiarismBtn =
    document.getElementById("humanizedPlagiarismBtn");

const copyBtn = document.getElementById("copyBtn");
const saveBtn = document.getElementById("saveBtn");
const downloadBtn = document.getElementById("downloadBtn");

const generatedContent =
    document.getElementById("generatedContent");
const humanizedContent =
    document.getElementById("humanizedContent");

const prompt = document.getElementById("prompt");
/* =====================================================
   PROMPT SUGGESTIONS
===================================================== */

const promptSuggestions = document.createElement("div");
promptSuggestions.className = "prompt-suggestions";
promptSuggestions.hidden = true;
promptSuggestions.setAttribute("aria-live", "polite");

prompt?.after(promptSuggestions);

function clearPromptSuggestions() {
    promptSuggestions.replaceChildren();
    promptSuggestions.hidden = true;
}

function showPromptSuggestions(values) {
    clearPromptSuggestions();

    if (!prompt || !Array.isArray(values)) return;

    const suggestions = [...new Set(
        values
            .filter(value => typeof value === "string")
            .map(value => value.trim())
            .filter(value => value.length >= 10 && value.length <= 180)
    )].slice(0, 3);

    if (!suggestions.length) return;

    const heading = document.createElement("strong");
    heading.textContent = "Suggested completions";
    promptSuggestions.appendChild(heading);

    const help = document.createElement("p");
    help.textContent = "Select a suggestion to complete your prompt.";
    promptSuggestions.appendChild(help);

    suggestions.forEach(value => {
        const button = document.createElement("button");

        button.type = "button";
        button.className = "prompt-suggestion-button";
        button.textContent = value;

        button.addEventListener("click", () => {
            prompt.value = value;

            prompt.dispatchEvent(
                new Event("input", { bubbles: true })
            );

            prompt.focus();
        });

        promptSuggestions.appendChild(button);
    });

    promptSuggestions.hidden = false;
}

let liveSuggestionTimer = null;
let liveSuggestionController = null;
let liveSuggestionVersion = 0;

function cancelLivePromptSuggestions() {
    clearTimeout(liveSuggestionTimer);

    liveSuggestionController?.abort();
    liveSuggestionController = null;

    liveSuggestionVersion++;
}

prompt?.addEventListener("input", function (event) {
    cancelLivePromptSuggestions();
    clearPromptSuggestions();

    // Selecting a suggestion fills the field without another API call.
    if (!event.isTrusted) return;

    const topic = prompt.value.trim();

    if (topic.length < 4 || topic.length > 3000) return;

    const version = liveSuggestionVersion;

    liveSuggestionTimer = setTimeout(async function () {
        if (generatorRequestBusy) return;

        const controller = new AbortController();
        liveSuggestionController = controller;

        

        const headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        };

        const csrf =
            document.querySelector('meta[name="csrf-token"]')?.content ||
            document.querySelector('input[name="csrf_token"]')?.value;

        if (csrf) headers["X-CSRFToken"] = csrf;

        try {
            const response = await fetch(
                "/user/api/prompt-suggestions",
                {
                    method: "POST",
                    credentials: "same-origin",
                    headers,
                    body: JSON.stringify({ prompt: topic }),
                    signal: controller.signal
                }
            );

            if (
                response.redirected ||
                !response.ok ||
                !(response.headers.get("content-type") || "")
                    .includes("application/json")
            ) {
                throw new Error("Suggestions unavailable.");
            }

            const result = await response.json();

            // Ignore responses for previous input.
            if (
                version !== liveSuggestionVersion ||
                prompt.value.trim() !== topic ||
                generatorRequestBusy
            ) {
                return;
            }

            showPromptSuggestions(
                result.success ? result.suggestions : []
            );

        } catch (error) {
            if (
                error.name !== "AbortError" &&
                version === liveSuggestionVersion
            ) {
                clearPromptSuggestions();
            }
        } finally {
            if (liveSuggestionController === controller) {
                liveSuggestionController = null;
            }
        }
    }, 1000);
});
const role = document.getElementById("role");
const contentType = document.getElementById("contentType");
const wordCount = document.getElementById("wordCount");

const generatedWords = document.getElementById("generatedWords");
const humanWords = document.getElementById("humanWords");
const contentActionSource =
    document.getElementById("generatorPdfSource");


/* =====================================================
   SELECTED CONTENT
===================================================== */

function getSelectedContent() {

    const selectedValue =
        contentActionSource?.value || "generatedContent";

    const isHumanized =
        selectedValue === "humanizedContent";

    const element = isHumanized
        ? humanizedContent
        : generatedContent;

    const content = element?.value?.trim() || "";

    return {
        element,
        content,
        isHumanized,
        sourceType: isHumanized
            ? "humanized"
            : "ai",
        label: isHumanized
            ? "Humanized content"
            : "AI content"
    };
}
let generatorRequestBusy = false;
let generatorNoticeTimer;
let generationAbort = null;


/* =====================================================
   NOTIFICATIONS
===================================================== */

function showGeneratorNotice(message, type = "info") {
    let notice = document.getElementById("generatorNotice");

    if (!notice) {
        notice = document.createElement("div");
        notice.id = "generatorNotice";
        notice.setAttribute("role", "status");
        notice.setAttribute("aria-live", "polite");
        notice.setAttribute("aria-atomic", "true");
        document.body.appendChild(notice);
    }

    clearTimeout(generatorNoticeTimer);

    const styles = {
        success: {
            color: "#168052",
            background: "#eaf8f0",
            icon: "fa-circle-check"
        },
        error: {
            color: "#dc3545",
            background: "#fff0f2",
            icon: "fa-circle-exclamation"
        },
        warning: {
            color: "#a66b08",
            background: "#fff6e5",
            icon: "fa-triangle-exclamation"
        },
        info: {
            color: "#6d28d9",
            background: "#f0e9ff",
            icon: "fa-circle-info"
        }
    };

    const style = styles[type] || styles.info;

    notice.style.setProperty("--notice-color", style.color);
    notice.style.setProperty(
        "--notice-background",
        style.background
    );

    const icon = document.createElement("span");
    icon.className = "notice-icon";
    icon.setAttribute("aria-hidden", "true");

    const symbol = document.createElement("i");
    symbol.className = `fas ${style.icon}`;
    icon.appendChild(symbol);

    const text = document.createElement("span");
    text.className = "notice-message";
    text.textContent = message;

    const close = document.createElement("button");
    close.type = "button";
    close.className = "notice-close";
    close.setAttribute("aria-label", "Dismiss notification");
    close.textContent = "×";

    close.addEventListener("click", () => {
        clearTimeout(generatorNoticeTimer);
        notice.hidden = true;
    });

    notice.replaceChildren(icon, text, close);
    notice.hidden = false;

    generatorNoticeTimer = setTimeout(() => {
        notice.hidden = true;
    }, type === "error" ? 6000 : 4000);
}


/* =====================================================
   REQUEST LOADER
===================================================== */

function beginGeneratorRequest(activeButton, label) {
    if (generatorRequestBusy) return null;

    generatorRequestBusy = true;

    const buttons = [
        generateBtn,
        regenerateBtn,
        humanizeBtn,
        copyBtn,
        saveBtn,
        downloadBtn,
        plagiarismBtn,
        humanizedPlagiarismBtn,
        document.getElementById("generatorPdfBtn"),
        prompt,
        role,
        contentType,
        wordCount,
        document.getElementById("generationMode"),
        document.getElementById("generatorPdfSource")
    ].filter(Boolean);

    const states = buttons.map(button => ({
        button,
        disabled: button.disabled,
        html: button.tagName === "BUTTON"
            ? button.innerHTML
            : null,
        busy: button.getAttribute("aria-busy")
    }));

    const fields = [
        generatedContent,
        humanizedContent
    ].filter(Boolean);

    const fieldStates = fields.map(field => ({
        field,
        readOnly: field.readOnly
    }));

    buttons.forEach(button => {
        button.disabled = true;
    });

    fields.forEach(field => {
        field.readOnly = true;
    });

    activeButton.setAttribute("aria-busy", "true");
    activeButton.innerHTML = `
        <i class="fas fa-spinner fa-spin" aria-hidden="true"></i>
        ${label}
    `;

    return () => {
        states.forEach(state => {
            state.button.disabled = state.disabled;

            if (state.html !== null) {
                state.button.innerHTML = state.html;
            }

            if (state.busy === null) {
                state.button.removeAttribute("aria-busy");
            } else {
                state.button.setAttribute("aria-busy", state.busy);
            }
        });

        fieldStates.forEach(state => {
            state.field.readOnly = state.readOnly;
        });

        generatorRequestBusy = false;
    };
}


/* =====================================================
   WORD COUNTERS
===================================================== */

function updateGeneratorWordCounts() {
    const count = text => {
        return text.trim()
            ? text.trim().split(/\s+/).length
            : 0;
    };

    if (generatedWords && generatedContent) {
        generatedWords.textContent =
            `${count(generatedContent.value)} Words`;
    }

    if (humanWords && humanizedContent) {
        humanWords.textContent =
            `${count(humanizedContent.value)} Words`;
    }
}

generatedContent?.addEventListener(
    "input",
    updateGeneratorWordCounts
);

humanizedContent?.addEventListener(
    "input",
    updateGeneratorWordCounts
);


/* =====================================================
   GENERATION MODE
===================================================== */

const generationMode = document.createElement("select");
generationMode.id = "generationMode";
generationMode.setAttribute("aria-label", "Generation mode");

for (const [value, label] of [
    ["quick", "Quick draft — live text"],
    ["detailed", "Detailed review — takes longer"]
]) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    generationMode.append(option);
}

const modeBox = document.createElement("div");
modeBox.className = "form-group";

const modeLabel = document.createElement("label");
modeLabel.htmlFor = "generationMode";
modeLabel.textContent = "Generation mode";

const modeNote = document.createElement("p");
modeNote.style.cssText = `
    font-size: 12px;
    line-height: 1.6;
    color: #655975;
    margin: 8px 0;
`;

function updateModeNote() {
    modeNote.textContent = generationMode.value === "quick"
        ? "Quick draft checks completion and length. External sources are not checked."
        : "Uses the existing factual-review pipeline. Content appears when the review finishes.";
}

generationMode.addEventListener("change", updateModeNote);
updateModeNote();

modeBox.append(modeLabel, generationMode, modeNote);
generateBtn?.before(modeBox);


/* =====================================================
   PROGRESS AND STOP BUTTON
===================================================== */

const generationStatus = document.createElement("p");
generationStatus.id = "generationStreamStatus";
generationStatus.setAttribute("role", "status");

generationStatus.style.cssText = `
    font-size: 13px;
    color: #654090;
    padding: 8px 12px;
    margin: 0;
    line-height: 1.6;
`;

generationStatus.hidden = true;
generatedContent?.before(generationStatus);

const stopGeneration = document.createElement("button");
stopGeneration.type = "button";
stopGeneration.textContent = "Stop";
stopGeneration.hidden = true;

stopGeneration.style.cssText = `
    margin-top: 8px;
    padding: 8px 16px;
    border: 1px solid #d9c9f1;
    border-radius: 10px;
    background: #fff;
    color: #65349c;
`;

generateBtn?.after(stopGeneration);

stopGeneration.addEventListener("click", () => {
    generationAbort?.abort();
});


/* =====================================================
   READ STREAMED JSON EVENTS
===================================================== */

async function readGenerationStream(response, onEvent) {
    if (!response.body) {
        throw new Error(
            "Live streaming is not available in this browser."
        );
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    let buffer = "";
    let completed = false;

    function consume(flush = false) {
        const lines = buffer.split("\n");
        buffer = flush ? "" : lines.pop();

        for (const line of lines) {
            if (!line.trim()) continue;

            const event = JSON.parse(line);
            if (completed) continue;

            onEvent(event);

            if (event.type === "done") {
                completed = true;
            }
        }
    }

    try {
        while (!completed) {
            const { value, done } = await reader.read();

            if (done) {
                buffer += decoder.decode();
                consume(true);
                break;
            }

            buffer += decoder.decode(value, {
                stream: true
            });

            if (buffer.length > 2000000) {
                throw new Error(
                    "The server response is too large."
                );
            }

            consume();
        }

        if (!completed) {
            throw new Error(
                "Connection ended before completion. Check My Content before trying again."
            );
        }
    } finally {
        try {
            await reader.cancel();
        } catch (_) {
            // Connection may already be closed.
        }

        reader.releaseLock();
    }
}


/* =====================================================
   GENERATE / REGENERATE
===================================================== */

generateBtn?.addEventListener("click", () => {
    generateContent(generateBtn);
});

regenerateBtn?.addEventListener("click", () => {
    if (!generatedContent?.value.trim()) {
        showGeneratorNotice(
            "Generate content first.",
            "warning"
        );
        return;
    }

    generateContent(regenerateBtn);
});

async function generateContent(activeButton = generateBtn) {
    if (
        generatorRequestBusy ||
        !generatedContent ||
        !activeButton
    ) {
        return;
    }

    if (!prompt?.value.trim()) {
        showGeneratorNotice("Please enter a topic.", "warning");
        prompt?.focus();
        return;
    }
        cancelLivePromptSuggestions();
    clearPromptSuggestions();
    const quick = generationMode.value === "quick";
    const regenerating = activeButton === regenerateBtn;

    const payload = {
        prompt: prompt.value,
        role: role?.value || "Student",
        content_type: contentType?.value || "Blog",
        word_count: wordCount?.value || "500"
    };

    const previous = generatedContent.value;

    const finish = beginGeneratorRequest(
        activeButton,
        regenerating ? "Regenerating…" : "Generating…"
    );

    if (!finish) return;

    generationAbort = new AbortController();
    const controller = generationAbort;

    let timedOut = false;
    let completed = false;
    let latestDraft = "";
    let saveState = "unknown";

    const timeout = setTimeout(() => {
        timedOut = true;
        controller.abort();
    }, quick ? 80000 : 360000);

    stopGeneration.hidden = false;
    generationStatus.hidden = false;

    generationStatus.textContent = quick
        ? "Preparing your draft…"
        : "Generating and reviewing content. This may take several minutes…";

    try {
        const headers = {
            "Content-Type": "application/json",
            "Accept": quick
                ? "application/x-ndjson"
                : "application/json"
        };

        const csrf =
            document.querySelector(
                'meta[name="csrf-token"]'
            )?.content ||
            document.querySelector(
                'input[name="csrf_token"]'
            )?.value;

        if (csrf) {
            headers["X-CSRFToken"] = csrf;
        }

        const response = await fetch("/user/generate", {
            method: "POST",
            credentials: "same-origin",
            headers,
            body: JSON.stringify(payload),
            signal: controller.signal
        });
        
console.log("GENERATE RESPONSE:", {
    status: response.status,
    redirected: response.redirected,
    url: response.url
});
        if (response.redirected || response.status === 401) {
            throw new Error(
                "Your session has expired. Please sign in again."
            );
        }

        const mime =
            response.headers.get("content-type") || "";

                if (!response.ok) {
            const errorData = mime.includes("application/json")
                ? await response.json()
                : {};

            const error = new Error(
                errorData.message ||
                "Unable to start generation. Please try again."
            );

            error.suggestions = errorData.suggestions || [];

            throw error;
        }
        function acceptFinal(data) {
            if (
                data.success !== true ||
                typeof data.content !== "string" ||
                !data.content.trim()
            ) {
                throw new Error(
                    data.message ||
                    "The server did not return a completed document."
                );
            }

            // Replace the visible draft only after server confirmation.
            generatedContent.value = data.content;

            if (humanizedContent) {
                humanizedContent.value = "";
            }

            completed = true;
            updateGeneratorWordCounts();

            generationStatus.textContent = quick
                ? "Draft saved. External sources were not checked; review factual claims before use."
                : "Content generated and saved.";

            showGeneratorNotice(
                regenerating
                    ? "Content regenerated and saved."
                    : "Content generated and saved.",
                "success"
            );
        }

        if (quick) {
            if (!mime.includes("application/x-ndjson")) {
                throw new Error(
                    "Streaming is not enabled on the server. Update the controller and restart Flask."
                );
            }

            await readGenerationStream(response, event => {
                if (event.type === "error") {
                    if (event.saved === false) {
                        saveState = "not-saved";
                    }

                    if (event.clear_content === true) {
                        latestDraft = "";
                    }

                    throw new Error(
                        event.message || "Generation failed."
                    );
                }

                if (event.type === "status") {
                    generationStatus.textContent = event.message;
                }

                if (event.type === "reset") {
                    // Do not clear the visible draft during repair.
                    // The first delta starts a new draft below.
                }

                if (
                    event.type === "delta" &&
                    typeof event.text === "string"
                ) {
                    const nearBottom =
                        generatedContent.scrollTop +
                        generatedContent.clientHeight >=
                        generatedContent.scrollHeight - 60;

                    if (!event.text) return;

                    if (!latestDraft && humanizedContent) {
                        humanizedContent.value = "";
                    }

                    latestDraft += event.text;
                    generatedContent.value = latestDraft;

                    updateGeneratorWordCounts();

                    if (nearBottom) {
                        generatedContent.scrollTop =
                            generatedContent.scrollHeight;
                    }
                }

                if (event.type === "done") {
                    acceptFinal(event);
                }
            });
        } else {
            if (!mime.includes("application/json")) {
                throw new Error(
                    "Unexpected server response."
                );
            }

            acceptFinal(await response.json());
        }
    } catch (error) {
        if (!completed) {
            const message = error.name === "AbortError"
                ? (
                    timedOut
                        ? "Generation timed out."
                        : "Generation stopped."
                )
                : error.message || "Unable to complete generation.";

            // A failed fresh generation must not leave an incomplete draft
            // looking like successful content. During regeneration, restore
            // the previously confirmed document instead.
            generatedContent.value = regenerating
                ? previous
                : "";

            if (!regenerating && humanizedContent) {
                humanizedContent.value = "";
            }

            generationStatus.textContent = regenerating && previous.trim()
                ? "Regeneration failed. Your previous content is unchanged."
                : "No completed draft was saved. Please try again.";

            updateGeneratorWordCounts();

            showGeneratorNotice(
                message,
                "error"
            );
            showPromptSuggestions(error.suggestions);
        }
    } finally {
        clearTimeout(timeout);
        generationAbort = null;
        stopGeneration.hidden = true;
        finish();
    }
}


/* =====================================================
   HUMANIZE
===================================================== */

humanizeBtn?.addEventListener("click", humanizeContent);

async function humanizeContent() {
    if (generatorRequestBusy) return;

    const sourceText = generatedContent?.value || "";

    if (!sourceText.trim()) {
        showGeneratorNotice("Generate content first.", "warning");
        return;
    }

    if (!humanizeBtn || !humanizedContent) return;

    const finish = beginGeneratorRequest(
        humanizeBtn,
        "Humanizing..."
    );

    if (!finish) return;

    try {
        const response = await fetch("/user/humanize", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                content: sourceText
            })
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(
                data.message || "Unable to humanize content."
            );
        }

        if (
            typeof data.content !== "string" ||
            !data.content.trim()
        ) {
            throw new Error(
                "Humanizer returned empty content."
            );
        }

        const originalWordCount =
            sourceText.trim().split(/\s+/).length;

        const humanizedWordCount =
            data.content.trim().split(/\s+/).length;

        if (humanizedWordCount < originalWordCount * 0.70) {
            throw new Error(
                "Humanized output appears incomplete. Please try again."
            );
        }

        humanizedContent.value = data.content;
        updateGeneratorWordCounts();

        showGeneratorNotice(
            "Content humanized successfully.",
            "success"
        );
    } catch (error) {
        console.error("HUMANIZE ERROR:", error);

        showGeneratorNotice(
            error instanceof SyntaxError
                ? "Unable to read the server response. Please try again."
                : error.message || "Unable to humanize content.",
            "error"
        );
    } finally {
        finish();
    }
}


/* =====================================================
   COPY GENERATED CONTENT
===================================================== */
/* =====================================================
   COPY SELECTED CONTENT
===================================================== */

copyBtn?.addEventListener("click", async () => {

    const selected = getSelectedContent();

    if (!selected.content) {

        showGeneratorNotice(
            `${selected.label} is empty.`,
            "warning"
        );

        return;
    }

    try {

        await navigator.clipboard.writeText(
            selected.content
        );

        showGeneratorNotice(
            `${selected.label} copied successfully.`,
            "success"
        );

    } catch (error) {

        console.error(
            "COPY CONTENT ERROR:",
            error
        );

        showGeneratorNotice(
            `Unable to copy ${selected.label.toLowerCase()}.`,
            "error"
        );
    }
});
/* =====================================================
   TXT EXPORT
===================================================== */

/* =====================================================
   EXPORT SELECTED CONTENT AS TXT
===================================================== */

downloadBtn?.addEventListener("click", () => {

    const selected = getSelectedContent();

    if (!selected.content) {

        showGeneratorNotice(
            `${selected.label} is empty.`,
            "warning"
        );

        return;
    }

    const blob = new Blob(
        [selected.content],
        {
            type: "text/plain;charset=utf-8"
        }
    );

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    const fileType = selected.isHumanized
        ? "Humanized_Content"
        : "AI_Content";

    link.href = url;
    link.download = `${fileType}.txt`;

    document.body.appendChild(link);

    link.click();
    link.remove();

    setTimeout(() => {
        URL.revokeObjectURL(url);
    }, 1000);

    showGeneratorNotice(
        `${selected.label} exported successfully.`,
        "success"
    );
});

/* =====================================================
   SAVE DOCUMENT
===================================================== */
/* =====================================================
   SAVE SELECTED CONTENT
===================================================== */

saveBtn?.addEventListener(
    "click",
    saveSelectedDocument
);


async function saveSelectedDocument() {

    const selected = getSelectedContent();

    if (!selected.content) {

        showGeneratorNotice(
            `${selected.label} is empty.`,
            "warning"
        );

        return;
    }

    if (!saveBtn || saveBtn.disabled) {
        return;
    }

    const originalHTML = saveBtn.innerHTML;

    saveBtn.disabled = true;
    saveBtn.setAttribute(
        "aria-busy",
        "true"
    );

    saveBtn.innerHTML = `
        <i
            class="fas fa-spinner fa-spin"
            aria-hidden="true"
        ></i>
        Saving...
    `;

    try {

        const response = await fetch(
            "/user/save-document",
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                credentials: "same-origin",

                body: JSON.stringify({

                    topic:
                        prompt?.value?.trim()
                        || "Untitled Content",

                    content:
                        selected.content,

                    content_type:
                        contentType?.value
                        || "Blog",

                    source_type:
                        selected.sourceType
                })
            }
        );

        const data = await response.json();

        if (
            !response.ok
            || data.success !== true
        ) {

            throw new Error(
                data.message
                || `Unable to save ${selected.label.toLowerCase()}.`
            );
        }

        showGeneratorNotice(
            `${selected.label} saved successfully.`,
            "success"
        );

    } catch (error) {

        console.error(
            "SAVE DOCUMENT ERROR:",
            error
        );

        showGeneratorNotice(
            error instanceof SyntaxError
                ? "Unable to read the server response."
                : (
                    error.message
                    || "Unable to save selected content."
                ),
            "error"
        );

    } finally {

        saveBtn.disabled = false;

        saveBtn.removeAttribute(
            "aria-busy"
        );

        saveBtn.innerHTML = originalHTML;
    }
}

/* =====================================================
   PROFESSIONAL PDF DOWNLOAD
   Canvas-based rendering prevents stretched text
===================================================== */

document.addEventListener("DOMContentLoaded", () => {

    const pdfButton =
        document.getElementById("generatorPdfBtn");

    const sourceSelect =
        document.getElementById("generatorPdfSource");

    if (!pdfButton || !sourceSelect) {
        return;
    }


    // =================================================
    // NOTIFICATION
    // =================================================

    function notify(message, type = "info") {

        if (typeof showGeneratorNotice === "function") {
            showGeneratorNotice(message, type);
            return;
        }

        alert(message);
    }


    // =================================================
    // CLEAN PDF TEXT
    // =================================================

    function cleanPdfText(value) {

        return String(value || "")
            .replace(/\r\n?/g, "\n")
            .replace(/[\u2018\u2019]/g, "'")
            .replace(/[\u201C\u201D]/g, '"')
            .replace(/[\u2013\u2014]/g, "-")
            .replace(/\u2026/g, "...")
            .replace(/\u00a0/g, " ")
            .replace(/\u2022/g, "-")
            .replace(/\t/g, "    ")
            .replace(
                /[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g,
                ""
            )
            .replace(/[ \t]+$/gm, "")
            .replace(/\n{3,}/g, "\n\n")
            .trim();
    }


    // =================================================
    // WRAP ONE PARAGRAPH
    // =================================================

    function wrapParagraph(
        context,
        paragraph,
        maximumWidth
    ) {

        const words = paragraph
            .replace(/\s+/g, " ")
            .trim()
            .split(" ");

        const lines = [];

        let currentLine = "";

        for (const originalWord of words) {

            let word = originalWord;

            /*
             * Break an extremely long word or URL
             * character by character.
             */
            while (
                context.measureText(word).width
                > maximumWidth
            ) {

                let part = "";

                for (const character of word) {

                    const testPart =
                        part + character;

                    if (
                        context.measureText(testPart).width
                        > maximumWidth
                    ) {
                        break;
                    }

                    part = testPart;
                }

                if (!part) {
                    break;
                }

                if (currentLine) {
                    lines.push(currentLine);
                    currentLine = "";
                }

                lines.push(part);

                word = word.slice(part.length);
            }

            if (!word) {
                continue;
            }

            const testLine =
                currentLine
                    ? `${currentLine} ${word}`
                    : word;

            if (
                context.measureText(testLine).width
                <= maximumWidth
            ) {
                currentLine = testLine;
            } else {

                if (currentLine) {
                    lines.push(currentLine);
                }

                currentLine = word;
            }
        }

        if (currentLine) {
            lines.push(currentLine);
        }

        return lines;
    }


    // =================================================
    // DOWNLOAD PDF
    // =================================================

    pdfButton.addEventListener("click", async () => {

        if (pdfButton.disabled) {
            return;
        }

        const selectedContent =
            document.getElementById(
                sourceSelect.value
            );

        const content = cleanPdfText(
            selectedContent?.value
            ?? selectedContent?.innerText
            ?? ""
        );

        const isHumanized =
            sourceSelect.value === "humanizedContent";

        if (!content) {

            notify(
                isHumanized
                    ? "Please humanize content before downloading PDF."
                    : "Please generate content before downloading PDF.",
                "error"
            );

            return;
        }

        if (!window.jspdf?.jsPDF) {

            notify(
                "PDF library is unavailable. Please reload the page.",
                "error"
            );

            return;
        }


        const buttonText =
            pdfButton.querySelector("span");

        const originalButtonText =
            buttonText?.textContent
            || "Download PDF";

        pdfButton.disabled = true;

        pdfButton.setAttribute(
            "aria-busy",
            "true"
        );

        if (buttonText) {
            buttonText.textContent =
                "Preparing PDF...";
        }


        try {

            await new Promise(resolve => {
                requestAnimationFrame(resolve);
            });

            const { jsPDF } = window.jspdf;


            // =============================================
            // CANVAS PAGE SETTINGS
            // A4 at approximately 150 DPI
            // =============================================

            const canvasWidth = 1240;
            const canvasHeight = 1754;

            const leftMargin = 115;
            const rightMargin = 115;
            const topMargin = 100;
            const bottomMargin = 105;

            const contentWidth =
                canvasWidth
                - leftMargin
                - rightMargin;

            const bottomLimit =
                canvasHeight
                - bottomMargin;

            const bodyFontSize = 25;
            const bodyLineHeight = 39;
            const paragraphGap = 22;

            const title =
                isHumanized
                    ? "Humanized Content"
                    : "Generated Content";

            const pages = [];

            let canvas = null;
            let context = null;
            let currentY = 0;


            // =============================================
            // CREATE CANVAS PAGE
            // =============================================

            function createPage(isFirstPage = false) {

                canvas =
                    document.createElement("canvas");

                canvas.width = canvasWidth;
                canvas.height = canvasHeight;

                context =
                    canvas.getContext("2d");

                // White PDF background
                context.fillStyle = "#ffffff";

                context.fillRect(
                    0,
                    0,
                    canvasWidth,
                    canvasHeight
                );

                context.textAlign = "left";

                context.textBaseline =
                    "alphabetic";

                context.direction = "ltr";


                if (isFirstPage) {

                    // PFCG label
                    context.fillStyle =
                        "#6d28d9";

                    context.font =
                        "700 22px Arial, sans-serif";

                    context.fillText(
                        "PFCG AI",
                        leftMargin,
                        topMargin
                    );


                    // Document title
                    context.fillStyle =
                        "#1f1648";

                    context.font =
                        "700 38px Arial, sans-serif";

                    context.fillText(
                        title,
                        leftMargin,
                        topMargin + 65
                    );


                    // Header line
                    context.strokeStyle =
                        "#ded7ec";

                    context.lineWidth = 2;

                    context.beginPath();

                    context.moveTo(
                        leftMargin,
                        topMargin + 95
                    );

                    context.lineTo(
                        canvasWidth - rightMargin,
                        topMargin + 95
                    );

                    context.stroke();

                    currentY =
                        topMargin + 145;

                } else {

                    currentY = topMargin;

                }


                // Normal body formatting
                context.fillStyle =
                    "#2d2d2d";

                context.font =
                    `${bodyFontSize}px Arial, sans-serif`;
            }


            // =============================================
            // SAVE CURRENT CANVAS PAGE
            // =============================================

            function finishCurrentPage() {

                if (canvas) {
                    pages.push(canvas);
                }
            }


            // =============================================
            // START FIRST PAGE
            // =============================================

            createPage(true);


            // =============================================
            // WRITE CONTENT
            // =============================================

            const paragraphs =
                content.split("\n");

            for (const originalParagraph of paragraphs) {

                const paragraph =
                    originalParagraph
                        .replace(/\s+/g, " ")
                        .trim();

                // Preserve blank paragraph spacing
                if (!paragraph) {

                    currentY += paragraphGap;

                    continue;
                }


                context.font =
                    `${bodyFontSize}px Arial, sans-serif`;

                const wrappedLines =
                    wrapParagraph(
                        context,
                        paragraph,
                        contentWidth
                    );


                for (const line of wrappedLines) {

                    /*
                     * Create a new page before a line
                     * reaches the footer area.
                     */
                    if (
                        currentY + bodyLineHeight
                        > bottomLimit
                    ) {

                        finishCurrentPage();

                        createPage(false);
                    }


                    // Reset body properties for every line
                    context.font =
                        `${bodyFontSize}px Arial, sans-serif`;

                    context.fillStyle =
                        "#2d2d2d";

                    context.textAlign =
                        "left";

                    context.direction =
                        "ltr";

                    /*
                     * fillText without maxWidth:
                     * prevents stretched/compressed letters.
                     */
                    context.fillText(
                        line,
                        leftMargin,
                        currentY
                    );

                    currentY += bodyLineHeight;
                }


                currentY += paragraphGap;


                if (currentY > bottomLimit) {

                    finishCurrentPage();

                    createPage(false);
                }
            }


            finishCurrentPage();


            // =============================================
            // ADD FOOTER TO ALL CANVAS PAGES
            // =============================================

            const totalPages = pages.length;

            pages.forEach((pageCanvas, index) => {

                const pageContext =
                    pageCanvas.getContext("2d");

                const footerY =
                    canvasHeight - 70;


                pageContext.strokeStyle =
                    "#e3e0e9";

                pageContext.lineWidth = 2;

                pageContext.beginPath();

                pageContext.moveTo(
                    leftMargin,
                    footerY - 30
                );

                pageContext.lineTo(
                    canvasWidth - rightMargin,
                    footerY - 30
                );

                pageContext.stroke();


                pageContext.fillStyle =
                    "#777180";

                pageContext.font =
                    "18px Arial, sans-serif";

                pageContext.textBaseline =
                    "alphabetic";


                // Footer left
                pageContext.textAlign = "left";

                pageContext.fillText(
                    "PFCG AI",
                    leftMargin,
                    footerY
                );


                // Footer right
                pageContext.textAlign = "right";

                pageContext.fillText(
                    `${index + 1} of ${totalPages}`,
                    canvasWidth - rightMargin,
                    footerY
                );
            });


            // =============================================
            // CREATE FINAL A4 PDF
            // =============================================

            const pdf = new jsPDF({

                orientation: "portrait",

                unit: "mm",

                format: "a4",

                compress: true

            });


            pdf.setProperties({

                title: title,

                subject:
                    "Content exported from PFCG AI",

                author: "PFCG AI",

                creator: "PFCG AI"

            });


            pages.forEach((pageCanvas, index) => {

                if (index > 0) {
                    pdf.addPage("a4", "portrait");
                }

                const pageImage =
                    pageCanvas.toDataURL(
                        "image/jpeg",
                        0.94
                    );

                pdf.addImage(
                    pageImage,
                    "JPEG",
                    0,
                    0,
                    210,
                    297,
                    undefined,
                    "FAST"
                );
            });


            // =============================================
            // DOWNLOAD
            // =============================================

            const date =
                new Date()
                    .toISOString()
                    .slice(0, 10);

            const fileType =
                isHumanized
                    ? "Humanized-Content"
                    : "AI-Content";

            pdf.save(
                `PFCG-${fileType}-${date}.pdf`
            );


            notify(
                "PDF downloaded successfully.",
                "success"
            );

        } catch (error) {

            console.error(
                "PDF export error:",
                error
            );

            notify(
                "Unable to download PDF. Please try again.",
                "error"
            );

        } finally {

            pdfButton.disabled = false;

            pdfButton.removeAttribute(
                "aria-busy"
            );

            if (buttonText) {
                buttonText.textContent =
                    originalButtonText;
            }
        }
    });
});
