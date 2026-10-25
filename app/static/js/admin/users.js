document.addEventListener("DOMContentLoaded", () => {
    const byId = id => document.getElementById(id);

    const viewModal = byId("viewUserModal");
    const editModal = byId("editUserModal");
    const editForm = byId("editUserForm");
    const notification = byId("adminNotification");
    const saveButton = byId("saveUserDetails");

    let currentModal = null;
    let returnFocus = null;
    let previousOverflow = "";
    let toastTimer = null;
    let editUrl = "";
    let saving = false;

    function setText(id, value) {
        const element = byId(id);
        if (element) element.textContent = value;
    }

    function showNotification(title, message, isError = false) {
        if (!notification) return;

        setText("notificationTitle", title);
        setText("notificationMessage", message);

        const icon = notification.querySelector(".notification-icon i");

        if (icon) {
            icon.className = isError
                ? "fas fa-triangle-exclamation"
                : "fas fa-check";
        }

        notification.classList.toggle("error", isError);
        notification.classList.add("show");

        clearTimeout(toastTimer);

        toastTimer = setTimeout(() => {
            notification.classList.remove("show");
        }, 5000);
    }

    function getUser(userId) {
        const row = byId("user-row-" + userId);
        if (!row) return null;

        return {
            row,
            id: row.dataset.userId,
            name: row.dataset.name || "",
            username: row.dataset.username || "",
            email: row.dataset.email || "",
            status: row.dataset.status || "active",
            generated: Number(row.dataset.generated || 0),
            humanized: Number(row.dataset.humanized || 0),
            plagiarism: Number(row.dataset.plagiarism || 0),
            seo: Number(row.dataset.seo || 0),
            feedback: Number(row.dataset.feedback || 0),
            total: Number(row.dataset.total || 0)
        };
    }

    function openModal(modal, trigger) {
        if (!modal || currentModal) return;

        currentModal = modal;
        returnFocus = trigger;
        previousOverflow = document.body.style.overflow;

        modal.classList.add("active");
        modal.setAttribute("aria-hidden", "false");
        document.body.style.overflow = "hidden";

        const first = modal.querySelector("button, input, select, textarea");
        if (first) first.focus();
    }

    function closeModal() {
        if (!currentModal || saving) return;

        currentModal.classList.remove("active");
        currentModal.setAttribute("aria-hidden", "true");
        currentModal = null;

        document.body.style.overflow = previousOverflow;

        if (returnFocus?.isConnected) returnFocus.focus();
        returnFocus = null;
    }

    document.querySelectorAll(".users-profile-image").forEach(image => {
        function showFallback() {
            image.hidden = true;
            const fallback = image.nextElementSibling;
            if (fallback) fallback.hidden = false;
        }

        image.addEventListener("error", showFallback);

        if (image.complete && image.naturalWidth === 0) {
            showFallback();
        }
    });

    document.querySelectorAll('[data-action="view"]').forEach(button => {
        button.addEventListener("click", () => {
            const user = getUser(button.dataset.userId);

            if (!user) {
                showNotification("Error", "User information was not found.", true);
                return;
            }

            setText("viewName", user.name || "No Name");
            setText("viewUsername", user.username ? "@" + user.username : "—");
            setText("viewEmail", user.email || "—");
            setText("viewStatus", user.status.replaceAll("_", " "));
            setText("viewGenerated", user.generated);
            setText("viewHumanized", user.humanized);
            setText("viewPlagiarism", user.plagiarism);
            setText("viewSeo", user.seo);
            setText("viewFeedback", user.feedback);
            setText("viewTotalActivity", user.total + " Total");

            openModal(viewModal, button);
        });
    });

    document.querySelectorAll('[data-action="edit"]').forEach(button => {
        button.addEventListener("click", () => {
            const user = getUser(button.dataset.userId);

            if (!user || !editForm) {
                showNotification("Error", "User information was not found.", true);
                return;
            }

            editUrl = button.dataset.editUrl;
            byId("editUserId").value = user.id;
            byId("editName").value = user.name;
            byId("editEmail").value = user.email;
            byId("editUsername").value = user.username;
            byId("editStatus").value = user.status.replaceAll("_", " ");
            byId("editReason").value = "";
            openModal(editModal, button);
        });
    });

    editForm?.addEventListener("submit", async event => {
        event.preventDefault();
        if (saving) return;

        const userId = byId("editUserId").value;
        const user = getUser(userId);

            const data = {
            name: byId("editName").value.trim(),
            email: user?.email || "",
            username: byId("editUsername").value.trim(),
            reason: byId("editReason").value.trim()
        };

        if (!user || !editUrl) {
            showNotification("Error", "Please reopen the edit form.", true);
            return;
        }

        if (!data.name || data.name.length > 100) {
            showNotification("Error", "Enter a name of 1 to 100 characters.", true);
            return;
        }

        if (data.username.length > 100) {
            showNotification("Error", "Username must not exceed 100 characters.", true);
            return;
        }

        saving = true;
        saveButton.disabled = true;
        saveButton.textContent = "Saving...";

        try {
            const headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            };

            const csrf = byId("usersCsrfToken");
            if (csrf) headers["X-CSRFToken"] = csrf.value;

            const response = await fetch(editUrl, {
                method: "POST",
                credentials: "same-origin",
                headers,
                body: JSON.stringify(data)
            });

            const result = await response.json().catch(() => null);

            if (!response.ok || !result?.success) {
                throw new Error(
                    result?.message || "Unable to update this user."
                );
            }

            user.row.dataset.name = data.name;
            user.row.dataset.username = data.username;

            const info = user.row.querySelector(".user-info");
            const name = info?.querySelector("strong");
            if (name) name.textContent = data.name;

            let username = info?.querySelector("small");

            if (data.username && info) {
                if (!username) {
                    username = document.createElement("small");
                    info.appendChild(username);
                }

                username.textContent = "@" + data.username;
            } else {
                username?.remove();
            }

            saving = false;
            closeModal();

            showNotification(
                "Success",
                result.message || "User details updated successfully."
            );
        } catch (error) {
            showNotification("Error", error.message, true);
        } finally {
            saving = false;
            saveButton.disabled = false;
            saveButton.textContent = "Save Changes";
        }
    });

    ["closeViewBtn", "closeEditBtn"].forEach(id => {
        byId(id)?.addEventListener("click", closeModal);
    });

    [viewModal, editModal].forEach(modal => {
        modal?.addEventListener("click", event => {
            if (event.target === modal) closeModal();
        });
    });

    document.addEventListener("keydown", event => {
        if (!currentModal) return;

        if (event.key === "Escape") {
            event.preventDefault();
            closeModal();
            return;
        }

        if (event.key !== "Tab") return;

        const items = [...currentModal.querySelectorAll(
            'button:not([disabled]), input:not([disabled]):not([type="hidden"]), ' +
            'select:not([disabled]), textarea:not([disabled]), a[href]'
        )].filter(element => element.getClientRects().length);

        if (!items.length) {
            event.preventDefault();
            return;
        }

        const first = items[0];
        const last = items[items.length - 1];

        if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
        }
    });

    byId("closeNotification")?.addEventListener("click", () => {
        clearTimeout(toastTimer);
        notification?.classList.remove("show");
    });
});