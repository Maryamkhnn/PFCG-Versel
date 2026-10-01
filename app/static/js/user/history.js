let box;
let allDocs = [];
let currentPage = 1;
const perPage = 5;

document.addEventListener("DOMContentLoaded", () => {

    box = document.getElementById("historyBox");

    if (!box) return;

    loadDocs();
});

// =========================
// LOAD DATA
// =========================

async function loadDocs() {

    const res = await fetch("/api/my-content", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({
            user_email: localStorage.getItem("userEmail")
        })
    });

    allDocs = await res.json();

    renderDocs();
}

// =========================
// RENDER
// =========================

function renderDocs() {

    if (!allDocs.length) {
        box.innerHTML = "<div class='card'>No documents found</div>";
        return;
    }

    const start = (currentPage - 1) * perPage;
    const end = start + perPage;

    const pageData = allDocs.slice(start, end);

    let html = "";

    pageData.forEach(doc => {

        html += `
        <div class="card">

            <h3>${doc.topic}</h3>

            <p>${(doc.content || "").substring(0, 200)}...</p>

            <button class="view-btn"
            onclick="viewDoc(${doc.id})">
            View
            </button>

            <button class="save-btn"
            onclick="saveDoc(${doc.id})">
            Save
            </button>

            <button class="delete-btn"
            onclick="deleteDoc(${doc.id})">
            Delete
            </button>

        </div>
        <br>
        `;
    });

    html += `
    <div style="margin-top:20px; display:flex; gap:10px;">
        <button class="pagination-btn"
        onclick="prevPage()">
        Prev
        </button>

        <button class="pagination-btn"
        onclick="nextPage()">
        Next
        </button>
    </div>
    `;

    box.innerHTML = html;
}

// =========================
// PAGINATION
// =========================

function nextPage() {
    if (currentPage * perPage < allDocs.length) {
        currentPage++;
        renderDocs();
    }
}

function prevPage() {
    if (currentPage > 1) {
        currentPage--;
        renderDocs();
    }
}

// =========================
// VIEW
// =========================

function viewDoc(id) {
    const doc = allDocs.find(d => d.id === id);
    if (doc) {
        alert(doc.content);
    }
}


// =========================
// DELETE
// =========================

async function deleteDoc(id) {

    if (!confirm("Are you sure you want to delete this document?")) return;

    const res = await fetch("/api/delete-content", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ id })
    });

    const data = await res.json();

    alert(data.message);

    loadDocs();
}
document.getElementById("searchBox")?.addEventListener("input", function() {

    const value = this.value.toLowerCase();

    const filtered = allDocs.filter(d =>
        d.topic.toLowerCase().includes(value)
    );

    const start = 0;
    const end = perPage;

    const pageData = filtered.slice(start, end);

    let html = "";

    pageData.forEach(doc => {

        html += `
        <div class="card">

            <h3>${doc.topic}</h3>

            <p>${(doc.content || "").substring(0, 200)}...</p>

            <button class="view-btn"
            onclick="viewDoc(${doc.id})">
            View
            </button>

            <button class="save-btn"
            onclick="saveDoc(${doc.id})">
            Save
            </button>

            <button class="delete-btn"
            onclick="deleteDoc(${doc.id})">
            Delete
            </button>

        </div>
        <br>
        `;
    });

    box.innerHTML = html;
});

document.getElementById("searchBox")?.addEventListener("input", function () {

    const value = this.value.toLowerCase();

    const filtered = allDocs.filter(d =>
        d.topic.toLowerCase().includes(value)
    );

    currentPage = 1;

    const start = 0;
    const end = perPage;

    const pageData = filtered.slice(start, end);

    let html = "";

    pageData.forEach(doc => {

        html += `
        <div class="card">
            <h3>${doc.topic}</h3>
            <p>${(doc.content || "").substring(0, 200)}...</p>

            <button class="view-btn"
            onclick="viewDoc(${doc.id})">
            View
            </button>

            <button class="save-btn"
            onclick="saveDoc(${doc.id})">
            Save
            </button>

            <button class="delete-btn"
            onclick="deleteDoc(${doc.id})">
            Delete
            </button>
        </div>
        <br>
        `;
    });

    box.innerHTML = html;
});

const searchInput = document.getElementById("searchContent");

if (searchInput) {

    searchInput.addEventListener("input", () => {

        const keyword = searchInput.value.toLowerCase();

        const cards = document.querySelectorAll("#historyBox .card");

        cards.forEach(card => {

            const text = card.innerText.toLowerCase();

            if (text.includes(keyword)) {
                card.style.display = "";
            } else {
                card.style.display = "none";
            }

        });

    });

}
async function saveDoc(id){

    const res = await fetch(
        "/api/save-document",
        {
            method:"POST",
            headers:{
                "Content-Type":"application/json"
            },
            body:JSON.stringify({
                id:id,
                user_email:
                localStorage.getItem("userEmail")
            })
        }
    );

    const data = await res.json();

    alert(data.message);
}

