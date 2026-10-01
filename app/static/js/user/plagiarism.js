/* ============================================================
   PFCG AI - PLAGIARISM CHECKER
   ============================================================ */


/* ============================================================
   INITIALIZE
   ============================================================ */

document.addEventListener("DOMContentLoaded", () => {

    const plagiarismBtn =
        document.getElementById("plagiarismBtn");

    const humanizedPlagiarismBtn =
        document.getElementById(
            "humanizedPlagiarismBtn"
        );


    /* --------------------------------------------------------
       AI PLAGIARISM BUTTON
       -------------------------------------------------------- */

    if (plagiarismBtn) {

        plagiarismBtn.addEventListener(
            "click",
            checkAIPlagiarism
        );

    }


    /* --------------------------------------------------------
       HUMANIZED PLAGIARISM BUTTON
       -------------------------------------------------------- */

    if (humanizedPlagiarismBtn) {

        humanizedPlagiarismBtn.addEventListener(
            "click",
            checkHumanizedPlagiarism
        );

    }

});


/* ============================================================
   GET GENERATED CONTENT
   ============================================================ */

function getGeneratedContent() {

    const element =
        document.getElementById(
            "generatedContent"
        );


    if (!element) {

        return "";

    }


    return element.value.trim();

}


/* ============================================================
   GET HUMANIZED CONTENT
   ============================================================ */

function getHumanizedContent() {

    const element =
        document.getElementById(
            "humanizedContent"
        );


    if (!element) {

        return "";

    }


    return element.value.trim();

}


/* ============================================================
   GET TOPIC
   ============================================================ */

function getTopic() {

    const element =
        document.getElementById(
            "prompt"
        );


    if (!element) {

        return "";

    }


    return element.value.trim();

}


/* ============================================================
   AI PLAGIARISM CHECK
   ============================================================ */

async function checkAIPlagiarism() {

    const content =
        getGeneratedContent();

    const topic =
        getTopic();

    const button =
        document.getElementById(
            "plagiarismBtn"
        );


    /* --------------------------------------------------------
       VALIDATE CONTENT
       -------------------------------------------------------- */

    if (!content) {

        showToast(
            "Generate content first.",
            "warning"
        );

        return;

    }


    /* --------------------------------------------------------
       BUTTON LOADING
       -------------------------------------------------------- */

    if (button) {

        button.disabled = true;

        button.innerHTML =
            '<i class="fas fa-spinner fa-spin"></i> Checking...';

    }


    try {

        /* ----------------------------------------------------
           SEND REQUEST
           ---------------------------------------------------- */

        const response =
            await fetch(
                "/user/plagiarism",
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body: JSON.stringify({

                        text:
                            content,

                        topic:
                            topic,

                        check_type:
                            "AI"

                    })

                }
            );


        /* ----------------------------------------------------
           READ RESPONSE
           ---------------------------------------------------- */

        const data =
            await response.json();


        console.log(
            "===================================="
        );

        console.log(
            "AI PLAGIARISM RESULT:"
        );

        console.log(
            data
        );

        console.log(
            "===================================="
        );


        /* ----------------------------------------------------
           CHECK SERVER RESPONSE
           ---------------------------------------------------- */

        if (
    !response.ok ||
    data.success === false
) {

    throw new Error(
        data.message ||
        "Unable to check plagiarism."
    );

}


        /* ----------------------------------------------------
           UPDATE AI RESULT
           ---------------------------------------------------- */

        updatePlagiarismResult(
            "ai",
            data
        );


        showToast(
            "AI plagiarism check completed.",
            "success"
        );


    }


    catch (error) {

        console.error(
            "AI PLAGIARISM ERROR:",
            error
        );


        showToast(
            error.message ||
            "Server Error",
            "error"
        );

    }


    finally {

        if (button) {

            button.disabled = false;

            button.innerHTML =
                '<i class="fas fa-search"></i> AI Check';

        }

    }

}


/* ============================================================
   HUMANIZED PLAGIARISM CHECK
   ============================================================ */

async function checkHumanizedPlagiarism() {

    const content =
        getHumanizedContent();

    const topic =
        getTopic();

    const button =
        document.getElementById(
            "humanizedPlagiarismBtn"
        );


    /* --------------------------------------------------------
       VALIDATE CONTENT
       -------------------------------------------------------- */

    if (!content) {

        showToast(
            "Humanize the content first.",
            "warning"
        );

        return;

    }


    /* --------------------------------------------------------
       BUTTON LOADING
       -------------------------------------------------------- */

    if (button) {

        button.disabled = true;

        button.innerHTML =
            '<i class="fas fa-spinner fa-spin"></i> Checking...';

    }


    try {

        /* ----------------------------------------------------
           SEND REQUEST
           ---------------------------------------------------- */

        const response =
            await fetch(
                "/user/plagiarism",
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body: JSON.stringify({

                        text:
                            content,

                        topic:
                            topic,

                        check_type:
                            "HUMANIZED"

                    })

                }
            );


        /* ----------------------------------------------------
           READ RESPONSE
           ---------------------------------------------------- */

        const data =
            await response.json();


        console.log(
            "===================================="
        );

        console.log(
            "HUMANIZED PLAGIARISM RESULT:"
        );

        console.log(
            data
        );

        console.log(
            "===================================="
        );


        /* ----------------------------------------------------
           CHECK SERVER RESPONSE
           ---------------------------------------------------- */

        if (
    !response.ok ||
    data.success === false
) {

    throw new Error(
        data.message ||
        "Unable to check plagiarism."
    );

}


        /* ----------------------------------------------------
           UPDATE HUMANIZED RESULT
           ---------------------------------------------------- */

        updatePlagiarismResult(
            "human",
            data
        );


        showToast(
            "Humanized plagiarism check completed.",
            "success"
        );


    }


    catch (error) {

        console.error(
            "HUMANIZED PLAGIARISM ERROR:",
            error
        );


        showToast(
            error.message ||
            "Server Error",
            "error"
        );

    }


    finally {

        if (button) {

            button.disabled = false;

            button.innerHTML =
                '<i class="fas fa-user-shield"></i> Humanized Check';

        }

    }

}


/* ============================================================
   UPDATE PLAGIARISM RESULT
   ============================================================ */

function updatePlagiarismResult(
    type,
    data
) {

    console.log(
        "===================================="
    );

    console.log(
        "UPDATING PLAGIARISM UI:"
    );

    console.log(
        data
    );

    console.log(
        "===================================="
    );


    /* --------------------------------------------------------
       GET PLAGIARISM SCORE
       
       Backend can return:
       plagiarism_percentage
       percentage
       score
       -------------------------------------------------------- */

    const percentage =
        Number(

            data.plagiarism_percentage ??

            data.percentage ??

            data.score ??

            0

        );


    /* --------------------------------------------------------
       KEEP SCORE BETWEEN 0 AND 100
       -------------------------------------------------------- */

    const safePercentage =
        Math.max(
            0,
            Math.min(
                100,
                percentage
            )
        );
        /* --------------------------------------------------------
       SEARCH COVERAGE AND STATUS
       -------------------------------------------------------- */


    console.log(
        "FINAL UI PERCENTAGE:",
        safePercentage
    );


    /* --------------------------------------------------------
       ELEMENT VARIABLES
       -------------------------------------------------------- */

    let percentageElement;

    let resultElement;

    let progressElement;

    let sourcesElement;


    /* ========================================================
       AI
       ======================================================== */

    if (type === "ai") {

        percentageElement =
            document.getElementById(
                "aiPercentage"
            );


        resultElement =
            document.getElementById(
                "aiPlagiarismResult"
            );


        progressElement =
            document.getElementById(
                "aiProgress"
            );


        sourcesElement =
            document.getElementById(
                "aiMatchedSources"
            );

    }


    /* ========================================================
       HUMANIZED
       ======================================================== */

    else {

        percentageElement =
            document.getElementById(
                "humanPercentage"
            );


        resultElement =
            document.getElementById(
                "humanizedPlagiarismResult"
            );


        progressElement =
            document.getElementById(
                "humanProgress"
            );


        sourcesElement =
            document.getElementById(
                "humanizedMatchedSources"
            );

    }


    /* ========================================================
       UPDATE PERCENTAGE
       ======================================================== */

    if (percentageElement) {

        percentageElement.innerText =
            `${safePercentage.toFixed(2)}%`;

    }


    /* ========================================================
       UPDATE PROGRESS BAR
       ======================================================== */

    if (progressElement) {

        progressElement.style.width =
            `${safePercentage}%`;

    }


    /* ========================================================
       GET MATCHED SOURCES
       
       Supports different backend key names.
       ======================================================== */

    const sources =
        data.sources ??

        data.matched_sources ??

        data.matchedSources ??

        [];


    console.log(
        "MATCHED SOURCES:",
        sources
    );


    /* ========================================================
       RENDER SOURCES
       ======================================================== */

    renderSources(
        sourcesElement,
        sources
    );

}


/* ============================================================
   RENDER MATCHED SOURCES
   ============================================================ */

function renderSources(
    container,
    sources
) {

    if (!container) {

        console.warn(
            "Sources container not found."
        );

        return;

    }


    /* --------------------------------------------------------
       CLEAR OLD SOURCES
       -------------------------------------------------------- */

    container.innerHTML = "";


    /* --------------------------------------------------------
       NO SOURCES
       -------------------------------------------------------- */

    if (
        !Array.isArray(sources) ||
        sources.length === 0
    ) {

        container.innerHTML = `
            <p class="no-sources">
                No matched sources found.
            </p>
        `;

        return;

    }


    /* --------------------------------------------------------
       RENDER EACH SOURCE
       -------------------------------------------------------- */

    sources.forEach(
        (source, index) => {

            const item =
                document.createElement(
                    "div"
                );


            item.className =
                "source-item";


            /* ------------------------------------------------
               SOURCE TITLE
               ------------------------------------------------ */

            const title =
                source.title ||

                source.name ||

                "Matched Source";


            /* ------------------------------------------------
               SOURCE URL
               ------------------------------------------------ */

            const url =
                source.url ||

                source.link ||

                "#";


            /* ------------------------------------------------
               SIMILARITY
               ------------------------------------------------ */

            const similarity =
                Number(

                    source.similarity ??

                    source.score ??

                    0

                );


            /* ------------------------------------------------
               USER MATCHED TEXT
               ------------------------------------------------ */

            const matchedText =
                source.matched_text ||

                source.matchedText ||

                source.text ||

                "";


            /* ------------------------------------------------
               ORIGINAL SOURCE TEXT
               ------------------------------------------------ */

            const sourceText =
                source.source_text ||

                source.sourceText ||

                source.source_sentence ||

                source.sourceSentence ||

                "";


            /* ------------------------------------------------
               CREATE SOURCE CARD
               ------------------------------------------------ */

            item.innerHTML = `

                <div class="source-number">
                    Source ${index + 1}
                </div>


                <a
                    class="source-title"
                    href="${escapeHTML(url)}"
                    target="_blank"
                    rel="noopener noreferrer"
                >
                    ${escapeHTML(title)}
                </a>


                <div class="source-similarity">

                Match Strength:

                <strong>
                ${similarity.toFixed(2)}%
                </strong>

                </div>


                ${
                    url !== "#"

                    ? `

                        <a
                            class="visit-source"
                            href="${escapeHTML(url)}"
                            target="_blank"
                            rel="noopener noreferrer"
                        >

                            Visit Source

                            <i class="fas fa-external-link-alt"></i>

                        </a>

                    `

                    : ""

                }

            `;


            container.appendChild(
                item
            );

        }
    );

}


/* ============================================================
   HTML ESCAPE
   ============================================================ */

function escapeHTML(value) {

    return String(value)

        .replace(
            /&/g,
            "&amp;"
        )

        .replace(
            /</g,
            "&lt;"
        )

        .replace(
            />/g,
            "&gt;"
        )

        .replace(
            /"/g,
            "&quot;"
        )

        .replace(
            /'/g,
            "&#039;"
        );

}