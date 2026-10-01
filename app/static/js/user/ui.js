const menuBtn =
document.getElementById("menuBtn");

const sidebar =
document.getElementById("sidebar");

if (menuBtn) {


menuBtn.addEventListener("click", () => {

    sidebar.classList.toggle(
        "active"
    );
});


}

// const togglePassword =
// document.getElementById(
// "togglePassword"
// );

// if (togglePassword) {


// togglePassword.addEventListener(
// "click",
// () => {

//     const pass =
//     document.getElementById(
//     "loginPassword"
//     );

//     pass.type =
//     pass.type === "password"
//     ? "text"
//     : "password";
// });


// }

const links =
document.querySelectorAll(
".side-menu a"
);

links.forEach(link => {


if (
    link.href ===
    window.location.href
) {

    link.style.background =
    "rgba(255,255,255,.2)";
}


});
const toggleSidebar =
document.getElementById(
"toggleSidebar"
);

if(toggleSidebar){

toggleSidebar.addEventListener(
"click",
()=>{

sidebar.classList.toggle(
"sidebar-collapsed"
);

});

}
function showToast(message,type="info"){

    const toast=document.getElementById("toast");

    let icon="";

    switch(type){

        case "success":
            icon='<i class="fas fa-circle-check"></i> ';
            break;

        case "error":
            icon='<i class="fas fa-circle-xmark"></i> ';
            break;

        case "warning":
            icon='<i class="fas fa-triangle-exclamation"></i> ';
            break;

        default:
            icon='<i class="fas fa-circle-info"></i> ';
    }

    toast.className="";

    toast.classList.add(type);

    toast.classList.add("show");

    toast.innerHTML=icon+message;

    clearTimeout(window.toastTimer);

    window.toastTimer=setTimeout(()=>{

        toast.classList.remove("show");

    },3000);

}