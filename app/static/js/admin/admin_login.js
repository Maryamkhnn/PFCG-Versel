document.addEventListener("DOMContentLoaded", function () {

    // ==========================
    // Elements
    // ==========================

    const form = document.querySelector("form");
    const email = document.querySelector("input[name='email']");
    const password = document.getElementById("password");
    const togglePassword = document.getElementById("togglePassword");
    const loginBtn = document.getElementById("loginBtn");

    // ==========================
    // Auto Focus
    // ==========================

    if (email) {
        email.focus();
    }

    // ==========================
    // Show / Hide Password
    // ==========================

    if (togglePassword) {

        togglePassword.addEventListener("click", function (e) {

            e.preventDefault();

            if (password.type === "password") {

                password.type = "text";

                this.innerHTML = '<i class="fas fa-eye-slash"></i>';

            } else {

                password.type = "password";

                this.innerHTML = '<i class="fas fa-eye"></i>';

            }

        });

    }

    // ==========================
    // Caps Lock Warning
    // ==========================

    if (password) {

        password.addEventListener("keyup", function (event) {

            if (event.getModifierState("CapsLock")) {

                password.title = "Caps Lock is ON";

            } else {

                password.title = "";

            }

        });

    }

    // ==========================
    // Form Validation
    // ==========================

    form.addEventListener("submit", function (e) {

        const emailValue = email.value.trim();
        const passwordValue = password.value.trim();

        if (emailValue === "") {

            e.preventDefault();
            ("Please enter your email.");
            email.focus();
            return;

        }

        if (passwordValue === "") {

            e.preventDefault();
            showToast("Please enter your email.","warning");
            password.focus();
            return;

        }

        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

        if (!emailPattern.test(emailValue)) {

            e.preventDefault();
            showToast("Please enter a valid email address.","warning");
            email.focus();
            return;

        }

        // ==========================
        // Loading Button
        // ==========================

        loginBtn.disabled = true;
        loginBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Logging in...';

    });

});