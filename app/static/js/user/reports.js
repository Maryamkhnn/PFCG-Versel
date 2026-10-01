document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    const page = document.querySelector(".reports-page");

    if (!page) return;

    const search = document.getElementById("searchReports");
    const pageSizeSelect = document.getElementById("reportsPerPage");
    const resultCount = document.getElementById("reportsResultCount");
    const pagination = document.getElementById("reportsPagination");
    const noMatch = document.getElementById("reportsNoMatch");
    const clearButton = document.getElementById("clearReportsSearch");

    const cards = Array.from(
        page.querySelectorAll(".reports-container .report-card")
    );

    const reports = cards.map(card => ({
        element: card,
        searchableText: [
            card.dataset.topic || "",
            card.dataset.type || ""
        ].join(" ").toLowerCase()
    }));

    let currentPage = 1;

    function goToPage(number) {
        currentPage = number;
        render();

        page.querySelector(".reports-tools").scrollIntoView({
            behavior: "auto",
            block: "start"
        });

        const activeButton = pagination.querySelector(
            '[aria-current="page"]'
        );

        activeButton?.focus({ preventScroll: true });
    }

    function addButton(label, targetPage, disabled = false, numbered = false) {
        const button = document.createElement("button");

        button.type = "button";
        button.textContent = String(label);
        button.disabled = disabled;

        if (numbered) {
            button.setAttribute("aria-label", `Page ${targetPage}`);

            if (targetPage === currentPage) {
                button.setAttribute("aria-current", "page");
            }
        }

        button.addEventListener("click", () => {
            goToPage(targetPage);
        });

        pagination.appendChild(button);
    }

    function addEllipsis() {
        const span = document.createElement("span");
        span.textContent = "…";
        span.setAttribute("aria-hidden", "true");
        pagination.appendChild(span);
    }

    function renderPagination(totalPages) {
        pagination.replaceChildren();
        pagination.hidden = totalPages <= 1;

        if (totalPages <= 1) return;

        addButton(
            "Previous",
            currentPage - 1,
            currentPage === 1
        );

        const firstPage = Math.max(
            1,
            Math.min(currentPage - 2, totalPages - 4)
        );

        const lastPage = Math.min(totalPages, firstPage + 4);

        if (firstPage > 1) {
            addButton(1, 1, false, true);

            if (firstPage > 2) {
                addEllipsis();
            }
        }

        for (let number = firstPage; number <= lastPage; number++) {
            addButton(number, number, false, true);
        }

        if (lastPage < totalPages) {
            if (lastPage < totalPages - 1) {
                addEllipsis();
            }

            addButton(totalPages, totalPages, false, true);
        }

        addButton(
            "Next",
            currentPage + 1,
            currentPage === totalPages
        );
    }

    function render() {
        const keyword = search.value.trim().toLowerCase();
        const pageSize = Number(pageSizeSelect.value);

        // Search all reports, including cards on other pages.
        const filtered = reports.filter(report =>
            report.searchableText.includes(keyword)
        );

        const totalPages = Math.max(
            1,
            Math.ceil(filtered.length / pageSize)
        );

        currentPage = Math.max(
            1,
            Math.min(currentPage, totalPages)
        );

        const start = (currentPage - 1) * pageSize;
        const end = Math.min(start + pageSize, filtered.length);

        cards.forEach(card => {
            card.hidden = true;
        });

        filtered.slice(start, end).forEach(report => {
            report.element.hidden = false;
        });

        noMatch.hidden = !(reports.length > 0 && filtered.length === 0);

        if (filtered.length > 0) {
            resultCount.textContent =
                `Showing ${start + 1}–${end} of ${filtered.length} reports` +
                ` · Page ${currentPage} of ${totalPages}`;
        } else {
            resultCount.textContent = reports.length
                ? "0 matching reports"
                : "0 reports";
        }

        renderPagination(totalPages);
    }

    search.addEventListener("input", () => {
        currentPage = 1;
        render();
    });

    pageSizeSelect.addEventListener("change", () => {
        currentPage = 1;
        render();
    });

    clearButton.addEventListener("click", () => {
        search.value = "";
        currentPage = 1;
        render();
        search.focus();
    });

    render();
});