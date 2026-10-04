(() => {
    "use strict";

    document.addEventListener("DOMContentLoaded", () => {
        const el = id => document.getElementById(id);
        const openButton = el("openAccountDeletion");
        const dialog = el("accountDeletionDialog");

        if (!openButton || !dialog) return;

        const requestForm = el("accountDeletionRequestForm");
        const confirmForm = el("accountDeletionConfirmForm");
        const requestFields = el("accountDeletionRequestFields");
        const confirmFields = el("accountDeletionConfirmFields");
        const message = el("accountDeletionMessage");
        const requestButton = el("requestAccountDeletionCode");
        const confirmButton = el("confirmAccountDeletion");

        let csrfToken = "";
        let busy = false;
        let deleted = false;

        function showMessage(text, type = "info") {
            message.textContent = text;
            message.dataset.type = type;
            message.hidden = !text;
        }

        function setBusy(value) {
            busy = value;

            requestFields.disabled = value || !csrfToken;
            confirmFields.disabled = value || !csrfToken;

            el("closeAccountDeletion").disabled = value;
            el("cancelAccountDeletion").disabled = value;
            el("restartAccountDeletion").disabled = value;

            dialog.setAttribute("aria-busy", String(value));
        }

        async function api(url, payload) {
            const controller = new AbortController();
            const timeout = setTimeout(
                () => controller.abort(),
                45000
            );

            const headers = {
                Accept: "application/json"
            };

            if (payload !== undefined) {
                headers["Content-Type"] = "application/json";
                headers["X-Account-Deletion-CSRF"] = csrfToken;

                const frameworkCsrf = el("accountCsrf")?.value;

                if (frameworkCsrf) {
                    headers["X-CSRFToken"] = frameworkCsrf;
                }
            }

            try {
                const response = await fetch(url, {
                    method: payload === undefined ? "GET" : "POST",
                    headers,
                    body: payload === undefined
                        ? undefined
                        : JSON.stringify(payload),
                    credentials: "same-origin",
                    cache: "no-store",
                    signal: controller.signal
                });

                if (response.redirected || response.status === 401) {
                    throw new Error(
                        "Please sign in again before continuing."
                    );
                }

                const result = await response.json().catch(() => null);

                if (!response.ok || result?.success !== true) {
                    throw new Error(
                        result?.message ||
                        "Unable to complete the request. Please try again."
                    );
                }

                return result;
            } catch (error) {
                if (
                    error.name === "AbortError" ||
                    error instanceof TypeError
                ) {
                    throw new Error(
                        url.endsWith("/confirm")
                            ? "Deletion could not be confirmed. Check whether you can still sign in before trying again."
                            : "The request could not be confirmed. Check your connection and try again."
                    );
                }

                throw error;
            } finally {
                clearTimeout(timeout);
            }
        }

        function closeDialog() {
            if (busy) return;

            dialog.close();
            requestForm.reset();
            confirmForm.reset();
            csrfToken = "";
            showMessage("");
        }

        openButton.addEventListener("click", async () => {
            if (busy || dialog.open) return;

            deleted = false;
            csrfToken = "";
            requestForm.reset();
            confirmForm.reset();
            requestForm.hidden = false;
            confirmForm.hidden = true;

            dialog.showModal();
            setBusy(true);
            showMessage("Preparing your confirmation form…");

            try {
                const result = await api(
                    "/user/api/account/deletion"
                );

                const token = result.data?.csrf_token;

                if (typeof token !== "string" || !token) {
                    throw new Error(
                        "Unable to prepare the form. Close it and try again."
                    );
                }

                csrfToken = token;
                showMessage("");
            } catch (error) {
                showMessage(error.message, "error");
            } finally {
                setBusy(false);

                if (csrfToken) {
                    el("deletionPassword").focus();
                }
            }
        });

        el("closeAccountDeletion").addEventListener(
            "click",
            closeDialog
        );

        el("cancelAccountDeletion").addEventListener(
            "click",
            closeDialog
        );

        dialog.addEventListener("cancel", event => {
            event.preventDefault();
            closeDialog();
        });

        el("restartAccountDeletion").addEventListener("click", () => {
            if (busy) return;

            requestForm.reset();
            confirmForm.reset();
            requestForm.hidden = false;
            confirmForm.hidden = true;

            showMessage(
                "Enter your password to request a new code. " +
                "Wait at least 60 seconds after the previous request."
            );

            el("deletionPassword").focus();
        });

        requestForm.addEventListener("submit", async event => {
            event.preventDefault();

            if (busy || !csrfToken) return;
            if (!requestForm.reportValidity()) return;

            const password = el("deletionPassword").value;

            setBusy(true);
            requestButton.textContent = "Sending Code…";
            showMessage("");

            try {
                const result = await api(
                    "/user/api/account/deletion/request",
                    { current_password: password }
                );

                requestForm.reset();
                confirmForm.reset();

                requestForm.hidden = true;
                confirmForm.hidden = false;

                showMessage(result.message);
            } catch (error) {
                showMessage(error.message, "error");
            } finally {
                setBusy(false);
                requestButton.textContent = "Send Confirmation Code";

                if (!confirmForm.hidden) {
                    el("deletionCode").focus();
                }
            }
        });

        confirmForm.addEventListener("submit", async event => {
            event.preventDefault();

            if (busy || !csrfToken || deleted) return;
            if (!confirmForm.reportValidity()) return;

            const code = el("deletionCode").value.trim();
            const confirmation = el("deletionConfirmation").value;

            if (!/^[0-9]{6}$/.test(code)) {
                showMessage("Enter the 6-digit email code.", "error");
                el("deletionCode").focus();
                return;
            }

            if (confirmation !== "DELETE") {
                showMessage(
                    "Type DELETE exactly to confirm.",
                    "error"
                );
                el("deletionConfirmation").focus();
                return;
            }

            setBusy(true);
            confirmButton.textContent = "Deleting Account…";
            showMessage("");

            try {
                const result = await api(
                    "/user/api/account/deletion/confirm",
                    { code, confirmation }
                );

                deleted = true;

                requestForm.reset();
                confirmForm.reset();

                showMessage(result.message);

                // Replace the current page after session clearance.
                window.location.replace("/");
            } catch (error) {
                showMessage(error.message, "error");
            } finally {
                if (!deleted) {
                    setBusy(false);
                    confirmButton.textContent =
                        "Permanently Delete Account";
                }
            }
        });
    });
})();