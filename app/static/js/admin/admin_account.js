document.addEventListener("DOMContentLoaded", () => {
    const urls = window.adminAccountEndpoints;
    const messageBox = document.getElementById("accountMessage");
    const darkModeToggle = document.getElementById("darkModeToggle");

    function showMessage(message, type = "error") {
        messageBox.textContent = message;
        messageBox.className = `account-message ${type}`;
        messageBox.scrollIntoView({
            behavior: "smooth",
            block: "nearest"
        });
    }

    async function sendForm(form, url, body, headers = {}) {
        const button = form.querySelector('button[type="submit"]');
        const oldHtml = button.innerHTML;

        button.disabled = true;
        button.innerHTML =
            '<i class="fas fa-spinner fa-spin"></i> Saving...';

        try {
            const response = await fetch(url, {
                method: "POST",
                headers,
                body,
                credentials: "same-origin"
            });

            const contentType =
                response.headers.get("content-type") || "";

            if (!contentType.includes("application/json")) {
                throw new Error(
                    response.status === 401
                        ? "Session expired. Please sign in again."
                        : "Unexpected response from server."
                );
            }

            const result = await response.json();

            if (!response.ok || !result.success) {
                throw new Error(
                    result.message || "Unable to save changes."
                );
            }

            return result;
        } finally {
            button.disabled = false;
            button.innerHTML = oldHtml;
        }
    }

    document
        .getElementById("accountProfileForm")
        .addEventListener("submit", async (event) => {
            event.preventDefault();

            const form = event.currentTarget;
            const name = document
                .getElementById("accountName")
                .value.trim();
            const email = document
                .getElementById("accountEmail")
                .value.trim()
                .toLowerCase();

            try {
                const result = await sendForm(
                    form,
                    urls.profile,
                    JSON.stringify({ name, email }),
                    { "Content-Type": "application/json" }
                );

                document.getElementById(
                    "accountDisplayName"
                ).textContent = name;

                document.getElementById(
                    "accountDisplayEmail"
                ).textContent = email;

                showMessage(
                    result.message || "Profile updated successfully.",
                    "success"
                );
            } catch (error) {
                showMessage(error.message);
            }
        });

    document
        .getElementById("accountPasswordForm")
        .addEventListener("submit", async (event) => {
            event.preventDefault();

            const form = event.currentTarget;
            const newPassword =
                document.getElementById("newPassword").value;
            const confirmPassword =
                document.getElementById("confirmPassword").value;

            if (newPassword !== confirmPassword) {
                showMessage("New passwords do not match.");
                return;
            }

            try {
                const result = await sendForm(
                    form,
                    urls.password,
                    new FormData(form)
                );

                form.reset();

                showMessage(
                    result.message || "Password changed successfully.",
                    "success"
                );
            } catch (error) {
                showMessage(error.message);
            }
        });

    document
        .getElementById("accountSettingsForm")
        .addEventListener("submit", async (event) => {
            event.preventDefault();

            const form = event.currentTarget;

            const data = {
                site_name: document
                    .getElementById("siteName")
                    .value.trim(),

                plagiarism_threshold: Number(
                    document.getElementById(
                        "plagiarismThreshold"
                    ).value
                ),

                seo_target_score: Number(
                    document.getElementById(
                        "seoTargetScore"
                    ).value
                ),

                default_word_limit: Number(
                    document.getElementById(
                        "defaultWordLimit"
                    ).value
                )
            };

            try {
                const result = await sendForm(
                    form,
                    urls.settings,
                    JSON.stringify(data),
                    { "Content-Type": "application/json" }
                );

                showMessage(
                    result.message || "Settings saved successfully.",
                    "success"
                );
            } catch (error) {
                showMessage(error.message);
            }
        });

    darkModeToggle.checked =
        localStorage.getItem("adminTheme") === "dark";

    document.documentElement.dataset.adminTheme =
        darkModeToggle.checked ? "dark" : "light";

    darkModeToggle.addEventListener("change", () => {
        const theme = darkModeToggle.checked
            ? "dark"
            : "light";

        localStorage.setItem("adminTheme", theme);
        document.documentElement.dataset.adminTheme = theme;
    });
});