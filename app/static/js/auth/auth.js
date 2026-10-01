document.addEventListener("DOMContentLoaded", function () {

    // =========================
    // PASSWORD TOGGLE
    // =========================

    const toggles = document.querySelectorAll(
        ".toggle-password, #togglePassword"
    );

    toggles.forEach(toggle => {

        toggle.addEventListener("click", function () {

            let targetId = this.dataset.target;
            let passwordInput;

            if (targetId) {
                passwordInput = document.getElementById(targetId);
            } else {
                passwordInput = document.getElementById("password");
            }

            if (!passwordInput) return;

            if (passwordInput.type === "password") {

                passwordInput.type = "text";

                this.innerHTML =
                    '<i class="fa-solid fa-eye-slash"></i>';

            } else {

                passwordInput.type = "password";

                this.innerHTML =
                    '<i class="fa-solid fa-eye"></i>';
            }

        });

    });


    // =========================
    // SIGNUP FORM
    // =========================

    const signupForm = document.getElementById("signupForm");

    if (signupForm) {

        const username = document.getElementById("username");
        const email = document.getElementById("email");
        const password = document.getElementById("password");

        const confirmPassword =
            document.getElementById("confirmPassword");

        const agree =
            document.getElementById("agree");


        const nameError =
            document.getElementById("nameError");

        const emailError =
            document.getElementById("emailError");

        const passwordError =
            document.getElementById("passwordError");

        const confirmError =
            document.getElementById("confirmError");

        const agreeError =
            document.getElementById("agreeError");


        const strengthBar =
            document.getElementById("strengthBar");

        const strengthText =
            document.getElementById("strengthText");


        // ERROR FUNCTION

        function setError(input, errorElement, message) {

            if (input) {

                input.classList.remove("valid");
                input.classList.add("invalid");

            }

            if (errorElement) {

                errorElement.innerHTML = message;

            }

        }


        // =========================
        // SUCCESS FUNCTION
        // =========================

        function setSuccess(input, errorElement) {

            if (input) {

                input.classList.remove("invalid");
                input.classList.add("valid");

            }

            if (errorElement) {

                errorElement.innerHTML = "";

            }

        }


        // =========================
        // PASSWORD REQUIREMENTS
        // =========================

        let passwordRules = null;


        if (password && strengthText) {

            passwordRules =
                document.createElement("div");

            passwordRules.id =
                "passwordRules";

            passwordRules.innerHTML = `

                <div class="password-rule" data-rule="length">
                    <i class="fa-solid fa-circle-xmark"></i>
                    <span>At least 8 characters</span>
                </div>

                <div class="password-rule" data-rule="upper">
                    <i class="fa-solid fa-circle-xmark"></i>
                    <span>One uppercase letter (A-Z)</span>
                </div>

                <div class="password-rule" data-rule="lower">
                    <i class="fa-solid fa-circle-xmark"></i>
                    <span>One lowercase letter (a-z)</span>
                </div>

                <div class="password-rule" data-rule="number">
                    <i class="fa-solid fa-circle-xmark"></i>
                    <span>One number (0-9)</span>
                </div>

                <div class="password-rule" data-rule="symbol">
                    <i class="fa-solid fa-circle-xmark"></i>
                    <span>One special symbol (@, #, $, !)</span>
                </div>

            `;


            strengthText.after(passwordRules);


            // Add styling dynamically
            const style =
                document.createElement("style");

            style.innerHTML = `

                #passwordRules {
                    margin-top: 10px;
                    padding: 10px 12px;
                    background: #f8f7ff;
                    border: 1px solid #eeeaff;
                    border-radius: 10px;
                }

                .password-rule {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-size: 12px;
                    color: #777;
                    margin: 5px 0;
                    transition: 0.2s;
                }

                .password-rule i {
                    font-size: 12px;
                    color: #b5b5b5;
                }

                .password-rule.valid {
                    color: #22a05a;
                }

                .password-rule.valid i {
                    color: #22c55e;
                }

                .password-rule.invalid {
                    color: #777;
                }

                .password-rule.invalid i {
                    color: #b5b5b5;
                }

            `;

            document.head.appendChild(style);

        }


        // =========================
        // UPDATE PASSWORD RULE
        // =========================

        function updatePasswordRule(
            ruleName,
            condition
        ) {

            if (!passwordRules) return;


            const rule =
                passwordRules.querySelector(
                    `[data-rule="${ruleName}"]`
                );


            if (!rule) return;


            const icon =
                rule.querySelector("i");


            if (condition) {

                rule.classList.add("valid");

                rule.classList.remove("invalid");


                if (icon) {

                    icon.className =
                        "fa-solid fa-circle-check";

                }

            } else {

                rule.classList.remove("valid");

                rule.classList.add("invalid");


                if (icon) {

                    icon.className =
                        "fa-solid fa-circle-xmark";

                }

            }

        }


        // =========================
        // NAME VALIDATION
        // =========================

        if (username) {

            username.addEventListener(
                "input",
                function () {

                    const originalValue =
                        this.value;


                    if (
                        /[^A-Za-z0-9\s]/.test(
                            originalValue
                        )
                    ) {

                        if (nameError) {

                            nameError.innerHTML =
                                "Only letters, numbers and spaces are allowed.";

                        }


                        this.value =
                            originalValue.replace(
                                /[^A-Za-z0-9\s]/g,
                                ""
                            );

                        return;

                    }


                    const value =
                        this.value.trim();


                    if (value === "") {

                        setError(
                            username,
                            nameError,
                            "Full name is required."
                        );

                        return;

                    }


                    if (value.length < 6) {

                        setError(
                            username,
                            nameError,
                            "Full name must contain at least 6 characters."
                        );

                        return;

                    }


                    setSuccess(
                        username,
                        nameError
                    );

                }
            );

        }


        // =========================
        // EMAIL VALIDATION
        // =========================

        if (email) {

            email.addEventListener(
                "input",
                function () {

                    const value =
                        this.value.trim();


                    const regex =
                        /^[^\s@]+@[^\s@]+\.[^\s@]+$/;


                    if (value === "") {

                        setError(
                            email,
                            emailError,
                            "Email is required."
                        );

                        return;

                    }


                    if (!regex.test(value)) {

                        setError(
                            email,
                            emailError,
                            "Enter a valid email address."
                        );

                        return;

                    }


                    setSuccess(
                        email,
                        emailError
                    );

                }
            );

        }


        // =========================
        // PASSWORD STRENGTH
        // =========================

        if (password) {

            password.addEventListener(
                "input",
                function () {

                    const value =
                        this.value;


                    // Password requirements

                    const hasLength =
                        value.length >= 8;

                    const hasUpper =
                        /[A-Z]/.test(value);

                    const hasLower =
                        /[a-z]/.test(value);

                    const hasNumber =
                        /[0-9]/.test(value);

                    const hasSymbol =
                        /[^A-Za-z0-9]/.test(value);


                    // Update requirements

                    updatePasswordRule(
                        "length",
                        hasLength
                    );

                    updatePasswordRule(
                        "upper",
                        hasUpper
                    );

                    updatePasswordRule(
                        "lower",
                        hasLower
                    );

                    updatePasswordRule(
                        "number",
                        hasNumber
                    );

                    updatePasswordRule(
                        "symbol",
                        hasSymbol
                    );


                    // Calculate strength

                    let score = 0;


                    if (hasLength) {
                        score++;
                    }

                    if (hasUpper) {
                        score++;
                    }

                    if (hasLower) {
                        score++;
                    }

                    if (hasNumber) {
                        score++;
                    }

                    if (hasSymbol) {
                        score++;
                    }


                    // Empty password

                    if (value.length === 0) {

                        if (strengthBar) {

                            strengthBar.style.width =
                                "0%";

                            strengthBar.style.background =
                                "#ececec";

                        }


                        if (strengthText) {

                            strengthText.innerHTML =
                                "Enter a strong password";

                        }


                        if (passwordError) {

                            passwordError.innerHTML =
                                "";

                        }


                        password.classList.remove(
                            "valid",
                            "invalid"
                        );

                        return;

                    }


                    // Password must meet ALL requirements

                    if (
                        !hasLength ||
                        !hasUpper ||
                        !hasLower ||
                        !hasNumber ||
                        !hasSymbol
                    ) {

                        setError(
                            password,
                            passwordError,
                            "Please meet all password requirements."
                        );

                    } else {

                        setSuccess(
                            password,
                            passwordError
                        );

                    }


                    // =========================
                    // STRENGTH BAR
                    // =========================

                    if (strengthBar) {

                        if (score <= 2) {

                            strengthBar.style.width =
                                "33%";

                            strengthBar.style.background =
                                "#ef4444";


                            if (strengthText) {

                                strengthText.innerHTML =
                                    "Weak Password";

                            }

                        } else if (score <= 4) {

                            strengthBar.style.width =
                                "66%";

                            strengthBar.style.background =
                                "#f59e0b";


                            if (strengthText) {

                                strengthText.innerHTML =
                                    "Medium Password";

                            }

                        } else {

                            strengthBar.style.width =
                                "100%";

                            strengthBar.style.background =
                                "#22c55e";


                            if (strengthText) {

                                strengthText.innerHTML =
                                    "Strong Password";

                            }

                        }

                    }

                }
            );

        }


        // =========================
        // CONFIRM PASSWORD
        // =========================

        if (
            confirmPassword &&
            password
        ) {

            confirmPassword.addEventListener(
                "input",
                function () {

                    if (
                        this.value !==
                        password.value
                    ) {

                        setError(
                            confirmPassword,
                            confirmError,
                            "Passwords do not match."
                        );

                        return;

                    }


                    if (
                        this.value === "" &&
                        password.value === ""
                    ) {

                        setError(
                            confirmPassword,
                            confirmError,
                            "Please confirm your password."
                        );

                        return;

                    }


                    setSuccess(
                        confirmPassword,
                        confirmError
                    );

                }
            );

        }


        // =========================
        // SIGNUP SUBMIT
        // =========================

        signupForm.addEventListener(
            "submit",
            function (e) {

                let valid = true;


                // NAME

                if (
                    !username ||
                    username.value.trim().length < 6
                ) {

                    valid = false;

                    setError(
                        username,
                        nameError,
                        "Full name must contain at least 6 characters."
                    );

                }


                // EMAIL

                if (
                    !email ||
                    !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(
                        email.value.trim()
                    )
                ) {

                    valid = false;

                    setError(
                        email,
                        emailError,
                        "Enter a valid email address."
                    );

                }


                // PASSWORD

                if (password) {

                    const value =
                        password.value;


                    const strongPassword =
                        value.length >= 8 &&
                        /[A-Z]/.test(value) &&
                        /[a-z]/.test(value) &&
                        /[0-9]/.test(value) &&
                        /[^A-Za-z0-9]/.test(value);


                    if (!strongPassword) {

                        valid = false;

                        setError(
                            password,
                            passwordError,
                            "Password must contain 8+ characters, uppercase, lowercase, number and special symbol."
                        );

                    }

                } else {

                    valid = false;

                }


                // CONFIRM PASSWORD

                if (
                    !confirmPassword ||
                    !password ||
                    password.value !==
                    confirmPassword.value
                ) {

                    valid = false;

                    setError(
                        confirmPassword,
                        confirmError,
                        "Passwords do not match."
                    );

                }


                // TERMS

                if (
                    agree &&
                    !agree.checked
                ) {

                    if (agreeError) {

                        agreeError.innerHTML =
                            "Please accept Terms & Conditions.";

                    }

                    valid = false;

                } else {

                    if (agreeError) {

                        agreeError.innerHTML =
                            "";

                    }

                }


                // STOP FORM IF INVALID

                if (!valid) {

                    e.preventDefault();

                }

            }
        );

    }


    // =========================
    // LOGIN FORM
    // =========================

    const loginForm =
        document.getElementById("loginForm");


    if (loginForm) {

        loginForm.addEventListener(
            "submit",
            function (e) {

                const emailInput =
                    document.querySelector(
                        '#loginForm input[name="email"]'
                    );


                const passwordInput =
                    document.querySelector(
                        '#loginForm input[name="password"]'
                    );


                if (
                    !emailInput ||
                    !passwordInput
                ) {

                    return;

                }


                const email =
                    emailInput.value.trim();


                const password =
                    passwordInput.value;


                // Email validation

                const emailRegex =
                    /^[^\s@]+@[^\s@]+\.[^\s@]+$/;


                if (
                    !emailRegex.test(email)
                ) {

                    e.preventDefault();


                    alert(
                        "Enter a valid email address."
                    );


                    return;

                }


                // Password validation

                if (
                    password.length < 8
                ) {

                    e.preventDefault();


                    alert(
                        "Password must be at least 8 characters."
                    );


                    return;

                }


                // Normal Flask form submission

            }
        );

    }

});