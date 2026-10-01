(() => {
    "use strict";

    document.addEventListener("DOMContentLoaded", () => {
        const page = document.getElementById("accountPage");
        if (!page) return;

        const el = (id) => document.getElementById(id);

        const endpoints = {
            profile: "/user/api/account",
            update: "/user/api/account/update",
            picture: "/user/api/account/picture",
            password: "/user/api/account/password"
        };

        let loaded = false;
        let busy = false;
        let toastTimer;
        let profile = {};

        function notify(message, type = "success") {
            const toast = el("accountToast");

            clearTimeout(toastTimer);

            toast.dataset.type = type;
            el("accountToastText").textContent = message;

            const icon = document.createElement("i");
            icon.className = type === "error"
                ? "fas fa-circle-exclamation"
                : "fas fa-check";

            toast.querySelector(".account-toast-icon")
                .replaceChildren(icon);

            toast.hidden = false;

            toastTimer = setTimeout(() => {
                toast.hidden = true;
            }, type === "error" ? 8000 : 5000);
        }

        el("closeAccountToast").addEventListener("click", () => {
            clearTimeout(toastTimer);
            el("accountToast").hidden = true;
        });

        function setBusy(value) {
            busy = value;

            el("accountProfileFields").disabled = busy || !loaded;
            el("accountPasswordFields").disabled = busy || !loaded;
            el("profilePicture").disabled = busy || !loaded;
            el("retryAccountBtn").disabled = busy;

            page.setAttribute("aria-busy", String(busy));
        }

        function loadingButton(button, label) {
            const original = button.innerHTML;
            const spinner = document.createElement("i");

            spinner.className = "fas fa-spinner fa-spin";
            spinner.setAttribute("aria-hidden", "true");

            button.replaceChildren(
                spinner,
                document.createTextNode(` ${label}`)
            );

            return () => {
                button.innerHTML = original;
            };
        }

        async function api(url, options = {}) {
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), 30000);
            const headers = new Headers(options.headers || {});
            const method = options.method || "GET";

            headers.set("Accept", "application/json");

            if (
                options.body !== undefined &&
                !(options.body instanceof FormData)
            ) {
                headers.set("Content-Type", "application/json");
            }

            const csrf = el("accountCsrf")?.value;

            if (csrf && method !== "GET") {
                headers.set("X-CSRFToken", csrf);
            }

            try {
                const response = await fetch(url, {
                    ...options,
                    method,
                    headers,
                    credentials: "same-origin",
                    cache: "no-store",
                    signal: controller.signal
                });

                if (response.status === 401 || response.redirected) {
                    throw new Error(
                        "Your session has expired. Please sign in again."
                    );
                }

                let data;

                try {
                    data = await response.json();
                } catch {
                    throw new Error(
                        "The server returned an unexpected response. Please try again."
                    );
                }

                if (!response.ok || data?.success !== true) {
                    throw new Error(
                        data?.message || "Unable to complete your request."
                    );
                }

                return data;
            } catch (error) {
                if (
                    error.name === "AbortError" ||
                    error instanceof TypeError
                ) {
                    throw new Error(
                        method === "GET"
                            ? "Unable to connect. Check your connection and try again."
                            : "The update could not be confirmed. Reload your account before trying again."
                    );
                }

                throw error;
            } finally {
                clearTimeout(timeout);
            }
        }

        function showPhoto(path) {
            const image = el("accountPhoto");
            const initials = el("accountInitials");

            image.onload = null;
            image.onerror = null;
            image.hidden = true;
            initials.hidden = false;
            image.removeAttribute("src");

            if (typeof path !== "string" || !path.trim()) return;

            try {
                const root = new URL(
                    page.dataset.staticRoot,
                    window.location.origin
                );

                const relativePath = path
                    .replace(/^\/+/, "")
                    .replace(/^static\//, "");

                const url = new URL(relativePath, root);

                if (
                    url.origin !== root.origin ||
                    !url.pathname.startsWith(root.pathname)
                ) {
                    return;
                }

                url.searchParams.set("v", Date.now());

                image.onload = () => {
                    image.hidden = false;
                    initials.hidden = true;
                };

                image.onerror = () => {
                    image.hidden = true;
                    initials.hidden = false;
                };

                image.src = url.href;
            } catch {
                image.hidden = true;
                initials.hidden = false;
            }
        }

        function displayProfile(data) {
            profile = { ...profile, ...data };

            const name = profile.name || profile.username || "User";

            el("accountName").textContent = name;
            el("accountEmail").textContent = profile.email || "";
            el("accountRole").textContent = profile.role || "Member";

            el("accountFullName").value = profile.name || "";
            el("accountUsername").value = profile.username || "";
            el("accountEmailInput").value = profile.email || "";

            el("accountInitials").textContent = name
                .trim()
                .split(/\s+/)
                .slice(0, 2)
                .map((part) => Array.from(part)[0] || "")
                .join("")
                .toUpperCase() || "U";

            showPhoto(profile.profile_picture);
        }

        async function loadAccount() {
            if (busy) return;

            loaded = false;
            setBusy(true);
            el("accountLoadError").hidden = true;

            try {
                const result = await api(endpoints.profile);

                if (
                    !result.data ||
                    typeof result.data !== "object" ||
                    Array.isArray(result.data)
                ) {
                    throw new Error("Your account details could not be loaded.");
                }

                displayProfile(result.data);
                loaded = true;
            } catch (error) {
                el("accountName").textContent = "Account unavailable";
                el("accountLoadMessage").textContent = error.message;
                el("accountLoadError").hidden = false;
            } finally {
                setBusy(false);
            }
        }

        el("retryAccountBtn").addEventListener("click", loadAccount);

        // SAVE PERSONAL DETAILS

        el("accountProfileForm").addEventListener("submit", async (event) => {
            event.preventDefault();
            if (busy || !loaded) return;

            const name = el("accountFullName").value.trim();
            const username = el("accountUsername").value.trim();

            if (!name) {
                notify("Please enter your full name.", "error");
                el("accountFullName").focus();
                return;
            }

            if (username.length < 3) {
                notify(
                    "Username must contain at least 3 characters.",
                    "error"
                );
                el("accountUsername").focus();
                return;
            }

            const restoreButton = loadingButton(
                el("saveAccountProfile"),
                "Saving…"
            );

            setBusy(true);

            try {
                const result = await api(endpoints.update, {
                    method: "POST",
                    body: JSON.stringify({ name, username })
                });

                displayProfile({
                    name,
                    username,
                    ...(result.data || {})
                });

                notify("Your profile has been updated.");
            } catch (error) {
                notify(error.message, "error");
            } finally {
                restoreButton();
                setBusy(false);
            }
        });

        // UPLOAD PHOTO

        el("profilePicture").addEventListener("change", async (event) => {
            const input = event.target;
            const file = input.files?.[0];

            if (!file || busy || !loaded) return;

            if (!/\.(png|jpe?g|webp)$/i.test(file.name)) {
                notify("Please select a JPG, PNG or WEBP image.", "error");
                input.value = "";
                return;
            }

            if (!file.size || file.size > 2 * 1024 * 1024) {
                notify("Please select an image smaller than 2 MB.", "error");
                input.value = "";
                return;
            }

            const formData = new FormData();
            formData.append("profile_picture", file);

            el("uploadLabel").textContent = "Uploading…";
            setBusy(true);

            try {
                const result = await api(endpoints.picture, {
                    method: "POST",
                    body: formData
                });

                const picture = result.data?.profile_picture;

                if (!picture) {
                    throw new Error(
                        "The photo update could not be confirmed. Reload your account."
                    );
                }

                profile.profile_picture = picture;
                showPhoto(picture);

                notify("Your profile photo has been updated.");
            } catch (error) {
                notify(error.message, "error");
            } finally {
                input.value = "";
                el("uploadLabel").textContent = "Change Photo";
                setBusy(false);
            }
        });

        // PASSWORD VISIBILITY

        const visibilityButtons = page.querySelectorAll(
            "[data-toggle-password]"
        );

        function setPasswordVisibility(button, visible) {
            const input = el(button.dataset.togglePassword);
            const label = page.querySelector(
                `label[for="${input.id}"]`
            ).textContent;

            input.type = visible ? "text" : "password";
            button.textContent = visible ? "Hide" : "Show";
            button.setAttribute("aria-pressed", String(visible));
            button.setAttribute(
                "aria-label",
                `${visible ? "Hide" : "Show"} ${label.toLowerCase()}`
            );
        }

        visibilityButtons.forEach((button) => {
            button.addEventListener("click", () => {
                const input = el(button.dataset.togglePassword);
                setPasswordVisibility(button, input.type === "password");
            });
        });

        // CHANGE PASSWORD

        el("accountPasswordForm").addEventListener("submit", async (event) => {
            event.preventDefault();
            if (busy || !loaded) return;

            const currentPassword = el("currentPassword").value;
            const newPassword = el("newPassword").value;
            const confirmPassword = el("confirmPassword").value;

            if (!currentPassword) {
                notify("Please enter your current password.", "error");
                el("currentPassword").focus();
                return;
            }

            if (newPassword.length < 8) {
                notify(
                    "Your new password must contain at least 8 characters.",
                    "error"
                );
                el("newPassword").focus();
                return;
            }

            if (newPassword !== confirmPassword) {
                notify("Your new passwords do not match.", "error");
                el("confirmPassword").focus();
                return;
            }

            if (currentPassword === newPassword) {
                notify(
                    "Choose a password different from your current password.",
                    "error"
                );
                el("newPassword").focus();
                return;
            }

            visibilityButtons.forEach((button) => {
                setPasswordVisibility(button, false);
            });

            const restoreButton = loadingButton(
                el("saveAccountPassword"),
                "Updating…"
            );

            setBusy(true);

            try {
                await api(endpoints.password, {
                    method: "POST",
                    body: JSON.stringify({
                        current_password: currentPassword,
                        new_password: newPassword,
                        confirm_password: confirmPassword
                    })
                });

                el("accountPasswordForm").reset();
                notify("Your password has been updated.");
            } catch (error) {
                notify(error.message, "error");
            } finally {
                restoreButton();
                setBusy(false);
            }
        });

        loadAccount();
    });
})();