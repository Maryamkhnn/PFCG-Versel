document.addEventListener("DOMContentLoaded", () => {
    const urls = window.adminAccountEndpoints || {};
    const messageBox = document.getElementById("accountMessage");
    const profileForm = document.getElementById("accountProfileForm");
    const passwordForm = document.getElementById("accountPasswordForm");
    const showPasswords = document.getElementById("showPasswords");
    const themeSelect = document.getElementById("accountTheme");
    const motionToggle = document.getElementById("accountReduceMotion");

    const root = document.documentElement;
    const systemTheme = window.matchMedia("(prefers-color-scheme: dark)");
    const systemMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

    function readPreference(key, fallback) {
        try {
            return localStorage.getItem(key) ?? fallback;
        } catch {
            return fallback;
        }
    }

    function savePreference(key, value) {
        try {
            localStorage.setItem(key, value);
            return true;
        } catch {
            showMessage(
                "Preference applied, but this browser could not save it."
            );
            return false;
        }
    }

    function showMessage(message, type = "error") {
        if (!messageBox) return;

        messageBox.hidden = false;
        messageBox.textContent = message;
        messageBox.className = `account-message ${type}`;

        messageBox.scrollIntoView({
            behavior: root.dataset.adminReduceMotion === "true"
                ? "auto"
                : "smooth",
            block: "nearest"
        });
    }

    async function sendForm(form, url, body, headers = {}) {
        if (!url) {
            throw new Error("Account endpoint is missing.");
        }

        const button = form.querySelector('button[type="submit"]');
        const originalHtml = button.innerHTML;

        button.disabled = true;
        button.innerHTML =
            '<i class="fas fa-spinner fa-spin" aria-hidden="true"></i> Saving...';

        try {
            const response = await fetch(url, {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    Accept: "application/json",
                    ...headers
                },
                body
            });

            if (response.status === 401 || response.redirected) {
                throw new Error("Session expired. Please sign in again.");
            }

            const contentType =
                response.headers.get("content-type") || "";

            if (!contentType.includes("application/json")) {
                throw new Error("Unexpected response from server.");
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
            button.innerHTML = originalHtml;
        }
    }

    /* PROFILE */
    profileForm?.addEventListener("submit", async event => {
        event.preventDefault();

        const nameInput = document.getElementById("accountName");
        const emailInput = document.getElementById("accountEmail");

        const name = nameInput.value.trim();
        const email = emailInput.value.trim().toLowerCase();

        if (!name || !email) {
            showMessage("Please enter your name and email address.");
            return;
        }

        try {
            const result = await sendForm(
                profileForm,
                urls.profile,
                JSON.stringify({ name, email }),
                { "Content-Type": "application/json" }
            );

            nameInput.value = name;
            emailInput.value = email;

            document.getElementById("accountDisplayName").textContent = name;
            document.getElementById("accountDisplayEmail").textContent = email;

            showMessage(
                result.message || "Profile updated successfully.",
                "success"
            );
        } catch (error) {
            showMessage(error.message);
        }
    });

    /* PASSWORD VISIBILITY */
    const passwordInputs = passwordForm
        ? [...passwordForm.querySelectorAll('input[type="password"]')]
        : [];

    function updatePasswordVisibility() {
        passwordInputs.forEach(input => {
            input.type = showPasswords?.checked ? "text" : "password";
        });
    }

    showPasswords?.addEventListener("change", updatePasswordVisibility);

    /* CHANGE PASSWORD */
    passwordForm?.addEventListener("submit", async event => {
        event.preventDefault();

        const newPassword =
            document.getElementById("newPassword").value;
        const confirmPassword =
            document.getElementById("confirmPassword").value;

        if (newPassword.length < 8) {
            showMessage("New password must have at least 8 characters.");
            return;
        }

        if (newPassword !== confirmPassword) {
            showMessage("New passwords do not match.");
            return;
        }

        try {
            const result = await sendForm(
                passwordForm,
                urls.password,
                new FormData(passwordForm)
            );

            passwordForm.reset();
            updatePasswordVisibility();

            showMessage(
                result.message || "Password changed successfully.",
                "success"
            );
        } catch (error) {
            showMessage(error.message);
        }
    });

    /* APPEARANCE */
    let themePreference = readPreference(
        "adminThemePreference",
        readPreference("adminTheme", "system")
    );

    if (!["light", "dark", "system"].includes(themePreference)) {
        themePreference = "system";
    }

    function applyTheme() {
        const theme = themePreference === "system"
            ? (systemTheme.matches ? "dark" : "light")
            : themePreference;

        root.dataset.adminTheme = theme;

        // Keep compatibility with the existing admin theme key.
        try {
            localStorage.setItem("adminTheme", theme);
        } catch {
            // Theme still applies without browser storage.
        }
    }

    applyTheme();

    if (themeSelect) {
        themeSelect.value = themePreference;

        themeSelect.addEventListener("change", () => {
            themePreference = themeSelect.value;
            applyTheme();

            if (savePreference("adminThemePreference", themePreference)) {
                showMessage("Appearance preference saved.", "success");
            }
        });
    }

    systemTheme.addEventListener("change", () => {
        if (themePreference === "system") applyTheme();
    });

    /* REDUCE MOTION */
    let reduceMotion = readPreference(
        "adminReduceMotion",
        String(systemMotion.matches)
    ) === "true";

    function applyMotion() {
        root.dataset.adminReduceMotion = String(reduceMotion);
    }

    applyMotion();

    if (motionToggle) {
        motionToggle.checked = reduceMotion;

        motionToggle.addEventListener("change", () => {
            reduceMotion = motionToggle.checked;
            applyMotion();

            if (savePreference("adminReduceMotion", String(reduceMotion))) {
                showMessage("Motion preference saved.", "success");
            }
        });
    }
});