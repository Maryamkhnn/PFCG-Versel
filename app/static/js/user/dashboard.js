// ==========================================
// PASSWORD SHOW / HIDE
// ==========================================

document.querySelectorAll(".toggle-password").forEach(button => {

    button.addEventListener("click", function () {

        const input = document.getElementById(this.dataset.target);
        const icon = this.querySelector("i");

        if (input.type === "password") {

            input.type = "text";

            icon.classList.remove("fa-eye");
            icon.classList.add("fa-eye-slash");

        }

        else {

            input.type = "password";

            icon.classList.remove("fa-eye-slash");
            icon.classList.add("fa-eye");

        }

    });

});


// ==========================================
// ELEMENTS
// ==========================================

const form = document.getElementById("signupForm");

const username = document.getElementById("username");
const email = document.getElementById("email");

const password = document.getElementById("password");
const confirmPassword = document.getElementById("confirmPassword");

const nameError = document.getElementById("nameError");
const emailError = document.getElementById("emailError");
const passwordError = document.getElementById("passwordError");
const confirmError = document.getElementById("confirmError");

const strengthBar = document.getElementById("strengthBar");
const strengthText = document.getElementById("strengthText");


// ==========================================
// PASSWORD STRENGTH
// ==========================================

password.addEventListener("input", function () {

    let value = this.value;

    let score = 0;

    if(value.length >= 8) score++;
    if(/[A-Z]/.test(value)) score++;
    if(/[a-z]/.test(value)) score++;
    if(/[0-9]/.test(value)) score++;
    if(/[^A-Za-z0-9]/.test(value)) score++;

    if(value===""){

        strengthBar.style.width="0%";
        strengthText.innerHTML="";
        return;

    }

    if(score<=2){

        strengthBar.style.width="33%";
        strengthBar.style.background="#ff4d4f";
        strengthText.innerHTML="Weak Password";

    }

    else if(score<=4){

        strengthBar.style.width="66%";
        strengthBar.style.background="#f7b731";
        strengthText.innerHTML="Medium Password";

    }

    else{

        strengthBar.style.width="100%";
        strengthBar.style.background="#2ecc71";
        strengthText.innerHTML="Strong Password";

    }

});


// ==========================================
// FORM VALIDATION
// ==========================================

form.addEventListener("submit",function(e){

    let valid=true;

    nameError.style.display="none";
    emailError.style.display="none";
    passwordError.style.display="none";
    confirmError.style.display="none";

    const name=username.value.trim();
    const mail=email.value.trim();
    const pass=password.value;
    const confirm=confirmPassword.value;

    const emailPattern=/^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const namePattern=/^[A-Za-z ]+$/;

    // NAME

    if(name===""){

        nameError.innerHTML="Please enter your full name.";

        nameError.style.display="block";

        valid=false;

    }

    else if(name.length<3){

        nameError.innerHTML="Name must be at least 3 characters.";

        nameError.style.display="block";

        valid=false;

    }

    else if(!namePattern.test(name)){

        nameError.innerHTML="Only letters are allowed.";

        nameError.style.display="block";

        valid=false;

    }


    // EMAIL

    if(mail===""){

        emailError.innerHTML="Please enter your email.";

        emailError.style.display="block";

        valid=false;

    }

    else if(!emailPattern.test(mail)){

        emailError.innerHTML="Please enter a valid email address.";

        emailError.style.display="block";

        valid=false;

    }


    // PASSWORD

    if(pass===""){

        passwordError.innerHTML="Please enter password.";

        passwordError.style.display="block";

        valid=false;

    }

    else if(pass.length<8){

        passwordError.innerHTML="Password must be at least 8 characters.";

        passwordError.style.display="block";

        valid=false;

    }


    // CONFIRM PASSWORD

    if(confirm===""){

        confirmError.innerHTML="Please confirm password.";

        confirmError.style.display="block";

        valid=false;

    }

    else if(pass!==confirm){

        confirmError.innerHTML="Passwords do not match.";

        confirmError.style.display="block";

        valid=false;

    }


    if(!valid){

        e.preventDefault();

    }

});