document.addEventListener("DOMContentLoaded", () => {
    const menuButton = document.getElementById("menuBtn");
    const sidebar = document.getElementById("sidebar");
    const closeButton = document.getElementById("closeSidebar");
    const overlay = document.getElementById("sidebarOverlay");

    if (!menuButton || !sidebar || !closeButton || !overlay) {
        return;
    }

    const mobileScreen = window.matchMedia("(max-width: 768px)");

    function setMenu(open, restoreFocus = true) {
        const shouldOpen = mobileScreen.matches && open;

        sidebar.classList.toggle("is-open", shouldOpen);
        document.body.classList.toggle("sidebar-open", shouldOpen);
        overlay.hidden = !shouldOpen;

        menuButton.setAttribute("aria-expanded", String(shouldOpen));
        menuButton.setAttribute(
            "aria-label",
            shouldOpen ? "Close navigation" : "Open navigation"
        );

        sidebar.inert = mobileScreen.matches && !shouldOpen;

        if (shouldOpen) {
            closeButton.focus();
        } else if (restoreFocus && mobileScreen.matches) {
            menuButton.focus();
        }
    }

    menuButton.addEventListener("click", () => {
        setMenu(!sidebar.classList.contains("is-open"));
    });

    closeButton.addEventListener("click", () => setMenu(false));
    overlay.addEventListener("click", () => setMenu(false));

    sidebar.querySelectorAll("a").forEach((link) => {
        link.addEventListener("click", () => setMenu(false, false));
    });

    document.addEventListener("keydown", (event) => {
        if (!sidebar.classList.contains("is-open")) {
            return;
        }

        if (event.key === "Escape") {
            setMenu(false);
        }

        if (event.key === "Tab") {
            const items = Array.from(
                sidebar.querySelectorAll("button, a[href]")
            ).filter((item) => !item.disabled && item.getClientRects().length);

            const first = items[0];
            const last = items[items.length - 1];

            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        }
    });

    mobileScreen.addEventListener("change", () => setMenu(false, false));
    setMenu(false, false);
});
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