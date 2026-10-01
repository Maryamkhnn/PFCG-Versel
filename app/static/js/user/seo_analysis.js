document.addEventListener("DOMContentLoaded", () => {
    initSEOPage();
});

const seoContentStore = new Map();

function initSEOPage() {

    const selector = document.getElementById("seoSelector");
    const loadBtn = document.getElementById("loadBtn");
    const analyzeBtn = document.getElementById("analyzeBtn");
    const contentArea = document.getElementById("seoContent");
    const keywordInput = document.getElementById("targetKeyword");

    if (!selector) {
        return;
    }

    loadAllContent();
    loadSEOHistory();

    if (loadBtn) {
        loadBtn.addEventListener(
            "click",
            loadSelectedContent
        );
    }

    selector.addEventListener("change", () => {
        if (!selector.value && contentArea) {
            delete contentArea.dataset.contentId;
            delete contentArea.dataset.sourceId;
            delete contentArea.dataset.sourceType;
            delete contentArea.dataset.contentTopic;
        }
    });

    if (analyzeBtn) {
        analyzeBtn.addEventListener(
            "click",
            analyzeSEO
        );
    }

    if (contentArea) {
        contentArea.addEventListener(
            "input",
            updateLiveWordCount
        );
    }

    if (keywordInput) {
        keywordInput.addEventListener(
            "keydown",
            (event) => {
                if (event.key === "Enter") {
                    event.preventDefault();
                    analyzeSEO();
                }
            }
        );
    }
}


function notify(message, type = "info") {

    if (typeof showToast === "function") {
        showToast(message, type);
        return;
    }

    alert(message);
}


async function loadAllContent() {

    const selector = document.getElementById("seoSelector");

    if (!selector) {
        return;
    }

    try {
        selector.disabled = true;

        selector.innerHTML = `
            <option value="">
                Loading your content...
            </option>
        `;

        const response = await fetch(
            "/user/api/my-content"
        );

        const result = await response.json();

        if (!response.ok || !result.success) {
            throw new Error(
                result.message || "Unable to load content."
            );
        }

        const contents = Array.isArray(result.data)
            ? result.data
            : [];

        selector.innerHTML = `
            <option value="">
                Select content to analyze
            </option>
        `;

        if (!contents.length) {
            selector.innerHTML += `
                <option value="" disabled>
                    No generated content found
                </option>
            `;
            return;
        }

        seoContentStore.clear();

        contents.forEach((item) => {
            const option = document.createElement("option");

            const sourceType = item.source_type === "humanized"
                ? "humanized"
                : "ai";

            const sourceId = Number(item.source_id || item.id);
            const contentKey = item.content_key
                || `${sourceType}-${sourceId}`;

            seoContentStore.set(contentKey, {
                ...item,
                source_type: sourceType,
                source_id: sourceId,
                content_key: contentKey
            });

            option.value = contentKey;
            option.textContent = `${
                sourceType === "humanized" ? "[Humanized]" : "[AI]"
            } ${item.topic || "Untitled Content"}`;

            selector.appendChild(option);
        });

    } catch (error) {
        console.error("LOAD CONTENT ERROR:", error);

        selector.innerHTML = `
            <option value="">
                Unable to load content
            </option>
        `;

        notify(
            "Unable to load saved content.",
            "error"
        );

    } finally {
        selector.disabled = false;
    }
}


async function loadSelectedContent() {

    const selector = document.getElementById("seoSelector");
    const loadBtn = document.getElementById("loadBtn");
    const contentArea = document.getElementById("seoContent");
    const topicElement = document.getElementById("contentTopic");
    const typeBadge = document.getElementById("contentTypeBadge");

    if (!selector || !contentArea) {
        return;
    }

    const contentKey = selector.value;

    if (!contentKey) {
        notify(
            "Please select content first.",
            "warning"
        );
        return;
    }

    try {
        if (loadBtn) {
            loadBtn.disabled = true;
            loadBtn.innerHTML = `
                <i class="fas fa-spinner fa-spin"></i>
                Loading...
            `;
        }

        const selected = seoContentStore.get(contentKey);

        if (!selected) {
            throw new Error("Selected content is no longer available.");
        }

        const response = await fetch(
            "/user/api/get-content",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    id: selected.source_id,
                    source_id: selected.source_id,
                    source_type: selected.source_type
                })
            }
        );

        const result = await response.json();

        if (!response.ok || !result.success) {
            throw new Error(
                result.message || "Unable to load content."
            );
        }

        const data = result.data || {};

        contentArea.value = data.content || "";
        contentArea.dataset.sourceId = String(
            data.source_id || selected.source_id
        );
        contentArea.dataset.sourceType = (
            data.source_type || selected.source_type
        );
        contentArea.dataset.contentTopic = (
            data.topic || selected.topic || "Untitled Content"
        );
        contentArea.dataset.contentId = (
            (data.source_type || selected.source_type) === "ai"
                ? String(data.source_id || selected.source_id)
                : ""
        );

        const titleInput = document.getElementById("seoTitle");
        const metaInput = document.getElementById("metaDescription");

        if (titleInput) titleInput.value = "";
        if (metaInput) metaInput.value = "";

        if (topicElement) {
            topicElement.textContent =
                data.topic || "Untitled Content";
        }

        if (typeBadge) {
            typeBadge.textContent = (
                (data.source_type || selected.source_type) === "humanized"
                    ? "Humanized"
                    : `AI · ${data.content_type || "Content"}`
            );
        }

        updateLiveWordCount();

        notify(
            "Content loaded successfully.",
            "success"
        );

    } catch (error) {
        console.error("LOAD SELECTED CONTENT ERROR:", error);

        notify(
            error.message || "Unable to load content.",
            "error"
        );

    } finally {
        if (loadBtn) {
            loadBtn.disabled = false;
            loadBtn.innerHTML = `
                <i class="fas fa-folder-open"></i>
                Load Content
            `;
        }
    }
}

async function analyzeSEO() {
    const contentArea = document.getElementById("seoContent");
    const keywordInput = document.getElementById("targetKeyword");
    const analyzeBtn = document.getElementById("analyzeBtn");
    const selector = document.getElementById("seoSelector");
    const loadBtn = document.getElementById("loadBtn");
    const seoTitleInput = document.getElementById("seoTitle");
    const metaInput = document.getElementById("metaDescription");

    if (!contentArea || !keywordInput || !analyzeBtn) {
        console.error("Required SEO page elements are missing.");
        return;
    }

    // Prevent duplicate requests without relying on disabled alone.
    if (analyzeBtn.dataset.busy === "true") return;

    if (contentArea.dataset.loading === "true") {
        notify("Please wait for your document to finish loading.", "info");
        return;
    }

    const content = contentArea.value.trim();
    const keyword = keywordInput.value.trim();

    if (!content) {
        notify("Please load or enter content first.", "warning");
        contentArea.focus();
        return;
    }

    if (!keyword) {
        notify("Please enter a target keyword.", "warning");
        keywordInput.focus();
        return;
    }

    // Use only the document actually loaded by loadSelectedContent().
    // If that tracking is absent, treat the text as manual content.
    const sourceId = contentArea.dataset.sourceId || null;
    const sourceType = sourceId
        ? (contentArea.dataset.sourceType || "ai")
        : "manual";
    const contentId = sourceType === "ai" ? sourceId : null;

    const contentTopic = sourceId
        ? (
            contentArea.dataset.contentTopic ||
            document.getElementById("contentTopic")?.textContent ||
            "Untitled Content"
        ).trim()
        : "Manual SEO Analysis";

    const originalButton = analyzeBtn.innerHTML;

    const controls = [
        selector,
        loadBtn,
        contentArea,
        keywordInput
    ].filter(Boolean);

    const previousDisabled = controls.map(
        (element) => element.disabled
    );

    analyzeBtn.dataset.busy = "true";
    analyzeBtn.disabled = true;

    controls.forEach((element) => {
        element.disabled = true;
    });

    analyzeBtn.innerHTML = `
        <i class="fas fa-spinner fa-spin" aria-hidden="true"></i>
        Analyzing...
    `;

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 45000);

    try {
        const headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        };

        const csrf = document.querySelector(
            'meta[name="csrf-token"]'
        )?.content || document.querySelector(
            'input[name="csrf_token"]'
        )?.value;

        if (csrf) headers["X-CSRFToken"] = csrf;

        const response = await fetch("/user/api/analyze-seo", {
            method: "POST",
            credentials: "same-origin",
            headers,
            signal: controller.signal,
            body: JSON.stringify({
                content,
                keyword,
                content_id: contentId,
                source_id: sourceId,
                source_type: sourceType,
                content_topic: contentTopic,
                seo_title: seoTitleInput?.value.trim() || "",
                meta_description: metaInput?.value.trim() || ""
            })
        });

        if (response.redirected || response.status === 401) {
            throw new Error(
                "Your session has expired. Please sign in again."
            );
        }

        const responseType =
            response.headers.get("content-type") || "";

        if (!responseType.includes("application/json")) {
            throw new Error(
                `The server returned an unexpected response (HTTP ${response.status}).`
            );
        }

        const result = await response.json();

        if (!response.ok || result.success !== true) {
            throw new Error(
                result.message || "Unable to analyze this content."
            );
        }

        const data = result.data;

        if (!data || typeof data !== "object") {
            throw new Error(
                "The server did not return an SEO report."
            );
        }

        const rawScore = Number(data.seo_score);
        const score = Number.isFinite(rawScore)
            ? Math.max(0, Math.min(100, rawScore))
            : 0;

        setText("wordCount", data.word_count ?? 0);
        setText("keywordCount", data.keyword_count ?? 0);
        setText("keywordDensity", `${data.keyword_density ?? 0}%`);
        setText("seoScore", `${score}%`);
        setText("seoStatus", data.seo_status || "Analyzed");
        setText("scoreLabel", data.seo_status || "Analyzed");

        const progress = document.getElementById("seoProgress");

        if (progress) {
            progress.style.width = `${score}%`;
        }

        const statusBox = document.getElementById("seoStatusBox");

        if (statusBox) {
            statusBox.classList.remove(
                "status-good",
                "status-medium",
                "status-low"
            );

            statusBox.classList.add(
                score >= 70
                    ? "status-good"
                    : score >= 50
                        ? "status-medium"
                        : "status-low"
            );
        }

        renderSuggestions(
            Array.isArray(data.suggestions)
                ? data.suggestions
                : []
        );

        notify(
            result.message ||
                "SEO analysis completed and saved automatically.",
            "success"
        );

        // History failure must not turn a successful analysis
        // into an "analysis failed" notification.
        try {
            await loadSEOHistory();
        } catch (historyError) {
            console.error("SEO HISTORY REFRESH ERROR:", historyError);
        }

    } catch (error) {
        console.error("SEO ANALYSIS ERROR:", error);

        const message = error.name === "AbortError"
            ? (
                "The request timed out. Check SEO History before "
                + "retrying; the report may already have been saved."
            )
            : error.message;

        notify(message || "Unable to complete SEO analysis.", "error");

    } finally {
        clearTimeout(timeout);

        analyzeBtn.dataset.busy = "false";
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = originalButton;

        controls.forEach((element, index) => {
            element.disabled = previousDisabled[index];
        });
    }
}
async function loadSEOHistory() {

    const body = document.getElementById("seoHistoryBody");

    if (!body) {
        return;
    }

    try {
        body.innerHTML = `
            <tr>
                <td colspan="4" class="empty-history">
                    <i class="fas fa-spinner fa-spin"></i>
                    Loading history...
                </td>
            </tr>
        `;

        const response = await fetch(
            "/user/api/seo-history"
        );

        const result = await response.json();

        if (!response.ok || !result.success) {
            throw new Error(
                result.message || "Unable to load SEO history."
            );
        }

        renderSEOHistory(result.data || []);

    } catch (error) {
        console.error("SEO HISTORY ERROR:", error);

        body.innerHTML = `
            <tr>
                <td colspan="4" class="empty-history">
                    Unable to load SEO history.
                </td>
            </tr>
        `;
    }
}


function renderSEOHistory(data) {

    const body = document.getElementById("seoHistoryBody");

    if (!body) {
        return;
    }

    body.innerHTML = "";

    if (!data.length) {
        body.innerHTML = `
            <tr>
                <td colspan="4" class="empty-history">
                    <i class="fas fa-chart-line"></i>
                    No SEO reports available yet.
                </td>
            </tr>
        `;
        return;
    }

    data.forEach((item) => {
        const score = Number(item.seo_score || 0);

        let scoreClass = "score-low";
        let statusClass = "status-low";

        if (score >= 80) {
            scoreClass = "score-high";
            statusClass = "status-high";
        } else if (score >= 50) {
            scoreClass = "score-medium";
            statusClass = "status-medium";
        }

        const row = document.createElement("tr");

        row.innerHTML = `
            <td>
                <div class="history-content">
                    <div class="history-icon">
                        <i class="fas fa-file-lines"></i>
                    </div>

                    <div>
                        <strong>
                            ${escapeHTML(
                                item.content_topic ||
                                "Untitled Content"
                            )}
                        </strong>

                        <small>
                            ${escapeHTML(sourceLabel(item.source_type))}
                            · ${item.word_count || 0} words
                        </small>
                    </div>
                </div>
            </td>

            <td>
                <span class="history-score ${scoreClass}">
                    ${score}%
                </span>
            </td>

            <td>
                <span class="history-status ${statusClass}">
                    ${escapeHTML(
                        item.seo_status ||
                        "Not Analyzed"
                    )}
                </span>
            </td>

            <td>
                <span class="history-date">
                    ${formatDate(item.created_at)}
                </span>
            </td>
        `;

        body.appendChild(row);
    });
}


function updateLiveWordCount() {

    const contentArea = document.getElementById("seoContent");
    const counter = document.getElementById("liveWordCount");

    if (!contentArea || !counter) {
        return;
    }

    const text = contentArea.value.trim();

    if (!text) {
        counter.textContent = "0";
        return;
    }

    counter.textContent = text.split(/\s+/).filter(
        (word) => word.length > 0
    ).length;
}


function updateStatusClass(score) {

    const box = document.getElementById("seoStatusBox");

    if (!box) {
        return;
    }

    box.classList.remove(
        "status-good",
        "status-medium",
        "status-low"
    );

    const numericScore = Number(score || 0);

    if (numericScore >= 80) {
        box.classList.add("status-good");
    } else if (numericScore >= 50) {
        box.classList.add("status-medium");
    } else {
        box.classList.add("status-low");
    }
}


function renderSuggestions(suggestions) {

    const list = document.getElementById("seoSuggestions");

    if (!list) {
        return;
    }

    list.innerHTML = "";

    if (!suggestions.length) {
        list.innerHTML = `
            <li class="empty-suggestion">
                <i class="fas fa-circle-check"></i>
                Excellent! No major SEO issues found.
            </li>
        `;
        return;
    }

    suggestions.forEach((suggestion) => {
        const item = document.createElement("li");

        item.innerHTML = `
            <i class="fas fa-check"></i>
            <span>${escapeHTML(suggestion)}</span>
        `;

        list.appendChild(item);
    });
}


function setText(id, value) {

    const element = document.getElementById(id);

    if (element) {
        element.textContent = value;
    }
}


function escapeHTML(value) {

    const div = document.createElement("div");

    div.textContent = value ?? "";

    return div.innerHTML;
}


function formatDate(value) {

    if (!value) {
        return "—";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return value;
    }

    return date.toLocaleDateString(
        "en-US",
        {
            day: "2-digit",
            month: "short",
            year: "numeric"
        }
    );
}


function sourceLabel(sourceType) {
    if (sourceType === "humanized") return "Humanized";
    if (sourceType === "ai") return "AI Content";
    return "Manual";
}
