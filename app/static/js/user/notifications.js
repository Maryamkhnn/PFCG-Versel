document.addEventListener(
    "DOMContentLoaded",
    function () {

        const bell =
            document.getElementById(
                "notificationBell"
            );

        const dropdown =
            document.getElementById(
                "notificationDropdown"
            );

        const countBadge =
            document.getElementById(
                "notificationCount"
            );

        const notificationList =
            document.getElementById(
                "notificationList"
            );

        const markAllButton =
            document.getElementById(
                "markAllNotificationsRead"
            );


        if (
            !bell
            || !dropdown
            || !countBadge
            || !notificationList
        ) {
            return;
        }


        let notificationsLoaded = false;


        // =================================================
        // SAFE HTML
        // =================================================

        function escapeHtml(value) {

            const element =
                document.createElement("div");

            element.textContent =
                value == null
                    ? ""
                    : String(value);

            return element.innerHTML;
        }


        // =================================================
        // DATE FORMAT
        // =================================================

        function formatDate(value) {

            if (!value) {
                return "";
            }

            const date =
                new Date(value);

            if (
                Number.isNaN(
                    date.getTime()
                )
            ) {
                return value;
            }

            return date.toLocaleString(
                undefined,
                {
                    dateStyle: "medium",
                    timeStyle: "short"
                }
            );
        }


        // =================================================
        // ICON
        // =================================================

        function getIcon(type) {

            const icons = {

                warn:
                    "fa-triangle-exclamation",

                warning:
                    "fa-triangle-exclamation",

                suspend:
                    "fa-ban",

                suspended:
                    "fa-ban",

                reactivate:
                    "fa-circle-check",

                reactivated:
                    "fa-circle-check",

                schedule_delete:
                    "fa-clock",

                cancel_delete:
                    "fa-rotate-left"

            };

            return (
                icons[type]
                || "fa-bell"
            );
        }


        // =================================================
        // VISUAL CLASS
        // =================================================

        function getVisualClass(type) {

            if (
                type === "warn"
                || type === "warning"
            ) {
                return "warning";
            }

            if (
                type === "suspend"
                || type === "suspended"
            ) {
                return "suspended";
            }

            if (
                type === "reactivate"
                || type === "reactivated"
            ) {
                return "reactivated";
            }

            return "";
        }


        // =================================================
        // UPDATE COUNT
        // =================================================

        function updateCount(count) {

            const safeCount =
                Math.max(
                    0,
                    Number(count) || 0
                );

            countBadge.textContent =
                safeCount > 99
                    ? "99+"
                    : String(safeCount);

            countBadge.hidden =
                safeCount === 0;

            if (markAllButton) {
                markAllButton.disabled =
                    safeCount === 0;
            }
        }


        // =================================================
        // RENDER
        // =================================================

        function renderNotifications(
            notifications
        ) {

            if (
                !Array.isArray(notifications)
                || notifications.length === 0
            ) {

                notificationList.innerHTML = `
                    <div class="notification-empty">

                        <i class="far fa-bell"></i>

                        No notifications yet.

                    </div>
                `;

                return;
            }


            notificationList.innerHTML =
                notifications
                    .map(function (item) {

                        const type =
                            String(
                                item.notification_type
                                || "notification"
                            ).toLowerCase();

                        const unread =
                            Number(item.is_read) === 0;

                        const visualClass =
                            getVisualClass(type);

                        return `
                            <article
                                class="
                                    notification-item
                                    ${unread ? "unread" : ""}
                                    ${visualClass}
                                "
                                data-notification-id="${
                                    Number(item.id)
                                }"
                                data-unread="${
                                    unread ? "1" : "0"
                                }"
                                tabindex="0"
                                role="button"
                                aria-label="Mark notification as read"
                            >

                                <div class="notification-item-icon">

                                    <i
                                        class="
                                            fas
                                            ${getIcon(type)}
                                        "
                                        aria-hidden="true"
                                    ></i>

                                </div>

                                <div class="notification-item-content">

                                    <strong>
                                        ${
                                            escapeHtml(
                                                item.title
                                                || "Notification"
                                            )
                                        }
                                    </strong>

                                    <p>
                                        ${
                                            escapeHtml(
                                                item.message
                                                || ""
                                            )
                                        }
                                    </p>

                                    <time>
                                        ${
                                            escapeHtml(
                                                formatDate(
                                                    item.created_at
                                                )
                                            )
                                        }
                                    </time>

                                </div>

                                ${
                                    unread
                                        ? `
                                            <span
                                                class="notification-unread-dot"
                                                aria-label="Unread"
                                            ></span>
                                        `
                                        : ""
                                }

                            </article>
                        `;

                    })
                    .join("");
        }


        // =================================================
        // LOAD NOTIFICATIONS
        // =================================================

        async function loadNotifications() {

            notificationList.setAttribute(
                "aria-busy",
                "true"
            );

            notificationList.innerHTML = `
                <div class="notification-loading">

                    Loading notifications...

                </div>
            `;


            try {

                const response =
                    await fetch(
                        "/user/api/notifications",
                        {
                            method: "GET",

                            headers: {
                                "Accept":
                                    "application/json"
                            }
                        }
                    );


                const result =
                    await response.json();


                if (
                    !response.ok
                    || !result.success
                ) {
                    throw new Error(
                        result.message
                        || "Unable to load notifications."
                    );
                }


                renderNotifications(
                    result.data || []
                );

                updateCount(
                    result.unread_count || 0
                );

                notificationsLoaded = true;


            } catch (error) {

                console.error(
                    "Notification load error:",
                    error
                );

                notificationList.innerHTML = `
                    <div class="notification-error">

                        <i
                            class="fas fa-circle-exclamation"
                        ></i>

                        Unable to load notifications.

                    </div>
                `;

            } finally {

                notificationList.setAttribute(
                    "aria-busy",
                    "false"
                );
            }
        }


        // =================================================
        // LOAD COUNT ONLY
        // =================================================

        async function loadUnreadCount() {

            try {

                const response =
                    await fetch(
                        "/user/api/notifications",
                        {
                            method: "GET",

                            headers: {
                                "Accept":
                                    "application/json"
                            }
                        }
                    );


                if (!response.ok) {
                    return;
                }


                const result =
                    await response.json();


                if (result.success) {

                    updateCount(
                        result.unread_count || 0
                    );
                }


            } catch (error) {

                console.error(
                    "Notification count error:",
                    error
                );
            }
        }


        // =================================================
        // MARK SINGLE AS READ
        // =================================================

        async function markAsRead(item) {

            if (
                !item
                || item.dataset.unread !== "1"
            ) {
                return;
            }


            const notificationId =
                Number(
                    item.dataset.notificationId
                );


            if (!notificationId) {
                return;
            }


            try {

                const response =
                    await fetch(
                        `/user/api/notifications/${notificationId}/read`,
                        {
                            method: "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            }
                        }
                    );


                const result =
                    await response.json();


                if (
                    !response.ok
                    || !result.success
                ) {
                    throw new Error(
                        result.message
                        || "Unable to update notification."
                    );
                }


                item.dataset.unread = "0";

                item.classList.remove(
                    "unread"
                );


                const dot =
                    item.querySelector(
                        ".notification-unread-dot"
                    );

                if (dot) {
                    dot.remove();
                }


                updateCount(
                    result.unread_count || 0
                );


            } catch (error) {

                console.error(
                    "Mark notification error:",
                    error
                );
            }
        }


        // =================================================
        // MARK ALL AS READ
        // =================================================

        async function markAllAsRead() {

            if (!markAllButton) {
                return;
            }


            markAllButton.disabled = true;


            try {

                const response =
                    await fetch(
                        "/user/api/notifications/read-all",
                        {
                            method: "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            }
                        }
                    );


                const result =
                    await response.json();


                if (
                    !response.ok
                    || !result.success
                ) {
                    throw new Error(
                        result.message
                        || "Unable to update notifications."
                    );
                }


                notificationList
                    .querySelectorAll(
                        ".notification-item"
                    )
                    .forEach(function (item) {

                        item.dataset.unread =
                            "0";

                        item.classList.remove(
                            "unread"
                        );


                        const dot =
                            item.querySelector(
                                ".notification-unread-dot"
                            );

                        if (dot) {
                            dot.remove();
                        }
                    });


                updateCount(0);


            } catch (error) {

                console.error(
                    "Mark all notifications error:",
                    error
                );

                markAllButton.disabled = false;
            }
        }


        // =================================================
        // BELL CLICK
        // =================================================

        bell.addEventListener(
            "click",
            async function (event) {

                event.stopPropagation();


                const willOpen =
                    dropdown.hidden;


                dropdown.hidden =
                    !willOpen;


                bell.setAttribute(
                    "aria-expanded",
                    String(willOpen)
                );


                if (
                    willOpen
                    && !notificationsLoaded
                ) {
                    await loadNotifications();
                }
            }
        );


        // =================================================
        // NOTIFICATION CLICK
        // =================================================

        notificationList.addEventListener(
            "click",
            function (event) {

                const item =
                    event.target.closest(
                        ".notification-item"
                    );

                markAsRead(item);
            }
        );


        notificationList.addEventListener(
            "keydown",
            function (event) {

                if (
                    event.key !== "Enter"
                    && event.key !== " "
                ) {
                    return;
                }


                const item =
                    event.target.closest(
                        ".notification-item"
                    );


                if (item) {

                    event.preventDefault();

                    markAsRead(item);
                }
            }
        );


        // =================================================
        // MARK ALL BUTTON
        // =================================================

        if (markAllButton) {

            markAllButton.addEventListener(
                "click",
                function (event) {

                    event.stopPropagation();

                    markAllAsRead();
                }
            );
        }


        // =================================================
        // OUTSIDE CLICK
        // =================================================

        document.addEventListener(
            "click",
            function (event) {

                if (
                    dropdown.hidden
                    || event.target.closest(
                        ".user-notification-area"
                    )
                ) {
                    return;
                }


                dropdown.hidden = true;

                bell.setAttribute(
                    "aria-expanded",
                    "false"
                );
            }
        );


        // =================================================
        // ESCAPE
        // =================================================

        document.addEventListener(
            "keydown",
            function (event) {

                if (
                    event.key === "Escape"
                    && !dropdown.hidden
                ) {

                    dropdown.hidden = true;

                    bell.setAttribute(
                        "aria-expanded",
                        "false"
                    );

                    bell.focus();
                }
            }
        );


        // Initial unread count
        loadUnreadCount();

    }
);