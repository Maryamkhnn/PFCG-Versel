// document.addEventListener("DOMContentLoaded", function () {

//     /* =====================================================
//        MODALS
//     ===================================================== */

//     const viewModal = document.getElementById("viewUserModal");
//     const editModal = document.getElementById("editUserModal");
//     const deleteModal = document.getElementById("deleteModal");

//     const closeViewBtn = document.getElementById("closeViewBtn");
//     const closeEditBtn = document.getElementById("closeEditBtn");
//     const cancelDeleteBtn = document.getElementById("cancelDeleteBtn");
//     const confirmDeleteBtn = document.getElementById("confirmDeleteBtn");


//     /* =====================================================
//        VIEW USER ELEMENTS
//     ===================================================== */

//     const viewName = document.getElementById("viewName");
//     const viewUsername = document.getElementById("viewUsername");
//     const viewEmail = document.getElementById("viewEmail");

//     const viewGenerated = document.getElementById("viewGenerated");
//     const viewHumanized = document.getElementById("viewHumanized");
//     const viewPlagiarism = document.getElementById("viewPlagiarism");
//     const viewSeo = document.getElementById("viewSeo");
//     const viewFeedback = document.getElementById("viewFeedback");
//     const viewTotalActivity = document.getElementById("viewTotalActivity");


//     /* =====================================================
//        EDIT USER ELEMENTS
//     ===================================================== */

//     const editForm = document.getElementById("editUserForm");

//     const editUserId = document.getElementById("editUserId");
//     const editName = document.getElementById("editName");
//     const editEmail = document.getElementById("editEmail");
//     const editUsername = document.getElementById("editUsername");


//     /* =====================================================
//        DELETE USER ELEMENTS
//     ===================================================== */

//     let selectedUserId = null;

//     const deleteUserName = document.getElementById("deleteUserName");


//     /* =====================================================
//        REGISTERED USERS COUNT
//     ===================================================== */

//     const registeredUsersCount =
//         document.getElementById("registeredUsersCount");


//     /* =====================================================
//        NOTIFICATION
//     ===================================================== */

//     const notification = document.getElementById("adminNotification");

//     const notificationTitle =
//         document.getElementById("notificationTitle");

//     const notificationMessage =
//         document.getElementById("notificationMessage");

//     const closeNotification =
//         document.getElementById("closeNotification");


//     function showNotification(title, message) {

//         if (!notification) {
//             return;
//         }

//         notificationTitle.textContent = title;
//         notificationMessage.textContent = message;

//         notification.classList.add("show");

//         setTimeout(function () {

//             notification.classList.remove("show");

//         }, 3000);
//     }


//     if (closeNotification) {

//         closeNotification.addEventListener("click", function () {

//             notification.classList.remove("show");

//         });
//     }


//     /* =====================================================
//        GET USER DATA FROM ROW
//     ===================================================== */

//     function getUserData(userId) {

//         const row =
//             document.getElementById("user-row-" + userId);

//         if (!row) {
//             return null;
//         }


//         return {

//             id: row.dataset.userId || userId,

//             name:
//                 row.dataset.name || "",

//             username:
//                 row.dataset.username || "",

//             email:
//                 row.dataset.email || "",

//             generated:
//                 parseInt(row.dataset.generated || "0", 10),

//             humanized:
//                 parseInt(row.dataset.humanized || "0", 10),

//             plagiarism:
//                 parseInt(row.dataset.plagiarism || "0", 10),

//             seo:
//                 parseInt(row.dataset.seo || "0", 10),

//             feedback:
//                 parseInt(row.dataset.feedback || "0", 10),

//          total:
//     parseInt(row.dataset.total || "0", 10),

// status:
//     (row.dataset.status || "active").toLowerCase()
//         };
//     }


//     /* =====================================================
//        VIEW USER
//     ===================================================== */

//     document.querySelectorAll(".view-btn").forEach(function (button) {

//         button.addEventListener("click", function () {

//             const userId = this.dataset.userId;

//             const user = getUserData(userId);


//             if (!user) {

//                 showNotification(
//                     "Error",
//                     "User information could not be found."
//                 );

//                 return;
//             }


//             viewName.textContent =
//                 user.name || "No Name";


//             viewUsername.textContent =
//                 user.username
//                     ? "@" + user.username
//                     : "-";


//             viewEmail.textContent =
//                 user.email || "-";


//             viewGenerated.textContent =
//                 user.generated;


//             viewHumanized.textContent =
//                 user.humanized;


//             viewPlagiarism.textContent =
//                 user.plagiarism;


//             viewSeo.textContent =
//                 user.seo;


//             viewFeedback.textContent =
//                 user.feedback;


//             viewTotalActivity.textContent =
//                 user.total + " Total";


//             if (viewModal) {
//                 viewModal.classList.add("active");
//             }

//         });

//     });


//     /* =====================================================
//        EDIT USER
//     ===================================================== */

//     document.querySelectorAll(".edit-btn").forEach(function (button) {

//         button.addEventListener("click", function () {

//             const userId = this.dataset.userId;

//             const user = getUserData(userId);


//             if (!user) {

//                 showNotification(
//                     "Error",
//                     "User information could not be found."
//                 );

//                 return;
//             }


//             editUserId.value =
//                 user.id;


//             editName.value =
//                 user.name;


//             editEmail.value =
//                 user.email;


//             editUsername.value =
//                 user.username;


//             if (editModal) {
//                 editModal.classList.add("active");
//             }

//         });

//     });


//     /* =====================================================
//        EDIT FORM SUBMIT
//     ===================================================== */

//     if (editForm) {

//         editForm.addEventListener("submit", async function (event) {

//             event.preventDefault();


//             const userId =
//                 editUserId.value;


//             const data = {

//                 name:
//                     editName.value.trim(),

//                 email:
//                     editEmail.value.trim(),

//                 username:
//                     editUsername.value.trim()

//             };


//             if (!userId) {

//                 showNotification(
//                     "Error",
//                     "User ID is missing."
//                 );

//                 return;
//             }


//             if (!data.name) {

//                 showNotification(
//                     "Error",
//                     "Name is required."
//                 );

//                 return;
//             }


//             if (!data.email) {

//                 showNotification(
//                     "Error",
//                     "Email is required."
//                 );

//                 return;
//             }


//             try {

//                 const response = await fetch(
//                     `/admin/users/${userId}/edit`,
//                     {
//                         method: "POST",

//                         headers: {
//                             "Content-Type": "application/json"
//                         },

//                         body: JSON.stringify(data)
//                     }
//                 );


//                 const result = await response.json();


//                 if (!response.ok || !result.success) {

//                     showNotification(
//                         "Error",
//                         result.message || "Unable to update user."
//                     );

//                     return;
//                 }


//                 /* =============================================
//                    UPDATE TABLE ROW WITHOUT REFRESH
//                 ============================================== */

//                 const row =
//                     document.getElementById(
//                         "user-row-" + userId
//                     );


//                 if (row) {


//                     /* UPDATE DATA ATTRIBUTES */

//                     row.dataset.name =
//                         data.name;

//                     row.dataset.email =
//                         data.email;

//                     row.dataset.username =
//                         data.username;


//                     /* UPDATE NAME */

//                     const nameElement =
//                         row.querySelector(
//                             ".user-info strong"
//                         );


//                     if (nameElement) {

//                         nameElement.textContent =
//                             data.name || "No Name";

//                     }


//                     /* UPDATE USERNAME */

//                     const userInfo =
//                         row.querySelector(".user-info");


//                     if (userInfo) {

//                         let usernameElement =
//                             userInfo.querySelector("small");


//                         if (data.username) {

//                             if (!usernameElement) {

//                                 usernameElement =
//                                     document.createElement("small");

//                                 userInfo.appendChild(
//                                     usernameElement
//                                 );
//                             }


//                             usernameElement.textContent =
//                                 "@" + data.username;

//                         } else {

//                             if (usernameElement) {
//                                 usernameElement.remove();
//                             }
//                         }
//                     }


//                     /* UPDATE EMAIL */

//                     const emailCell =
//                         row.querySelector(".email-cell");


//                     if (emailCell) {

//                         emailCell.textContent =
//                             data.email;

//                     }

//                 }


//                 if (editModal) {
//                     editModal.classList.remove("active");
//                 }


//                 showNotification(
//                     "Success",
//                     result.message ||
//                     "User updated successfully."
//                 );

//             }

//             catch (error) {

//                 console.error(
//                     "Edit user error:",
//                     error
//                 );


//                 showNotification(
//                     "Error",
//                     "Something went wrong while updating the user."
//                 );

//             }

//         });

//     }
//     /* =====================================================
//        DELETE USER BUTTON
//     ===================================================== */

//     document.querySelectorAll(".delete-btn").forEach(function (button) {

//         button.addEventListener("click", function () {

//             selectedUserId =
//                 this.dataset.userId;


//             if (!selectedUserId) {

//                 showNotification(
//                     "Error",
//                     "User ID is missing."
//                 );

//                 return;
//             }


//             const user =
//                 getUserData(selectedUserId);


//             if (!user) {

//                 showNotification(
//                     "Error",
//                     "User information could not be found."
//                 );

//                 selectedUserId = null;

//                 return;
//             }


//             if (deleteUserName) {

//                 const displayName =
//                     user.name || "this user";


//                 const displayEmail =
//                     user.email
//                         ? ` (${user.email})`
//                         : "";


//                 deleteUserName.textContent =
//                     displayName + displayEmail;
//             }


//             if (deleteModal) {
//                 deleteModal.classList.add("active");
//             }

//         });

//     });


//     /* =====================================================
//        CONFIRM DELETE
//     ===================================================== */

//     if (confirmDeleteBtn) {

//         confirmDeleteBtn.addEventListener(
//             "click",
//             async function () {


//                 if (!selectedUserId) {
//                     return;
//                 }


//                 confirmDeleteBtn.disabled = true;

//                 confirmDeleteBtn.innerHTML =
//                     '<i class="fas fa-spinner fa-spin"></i> Deleting...';


//                 try {

//                     const response = await fetch(
//                         `/admin/users/${selectedUserId}/delete`,
//                         {
//                             method: "POST",

//                             headers: {
//                                 "Content-Type": "application/json"
//                             }
//                         }
//                     );


//                     const result =
//                         await response.json();


//                     if (!response.ok || !result.success) {

//                         showNotification(
//                             "Error",
//                             result.message ||
//                             "Unable to delete user."
//                         );

//                         return;
//                     }


//                     /* =========================================
//                        REMOVE USER ROW
//                     ========================================== */

//                     const row =
//                         document.getElementById(
//                             "user-row-" + selectedUserId
//                         );


//                     if (row) {
//                         row.remove();
//                     }


//                     /* =========================================
//                        UPDATE REGISTERED USERS COUNT
//                     ========================================== */

//                     if (registeredUsersCount) {

//                         const currentCount =
//                             parseInt(
//                                 registeredUsersCount.textContent || "0",
//                                 10
//                             );


//                         if (currentCount > 0) {

//                             registeredUsersCount.textContent =
//                                 currentCount - 1;

//                         }
//                     }


//                     if (deleteModal) {
//                         deleteModal.classList.remove("active");
//                     }


//                     showNotification(
//                         "Success",
//                         result.message ||
//                         "User and related data deleted successfully."
//                     );


//                     selectedUserId = null;


//                     if (deleteUserName) {

//                         deleteUserName.textContent =
//                             "this user";

//                     }

//                 }

//                 catch (error) {

//                     console.error(
//                         "Delete user error:",
//                         error
//                     );


//                     showNotification(
//                         "Error",
//                         "Something went wrong while deleting the user."
//                     );

//                 }

//                 finally {

//                     confirmDeleteBtn.disabled =
//                         false;

//                     confirmDeleteBtn.innerHTML =
//                         '<i class="fas fa-trash"></i> Delete User';

//                 }

//             }
//         );

//     }


//     /* =====================================================
//        CLOSE VIEW MODAL
//     ===================================================== */

//     if (closeViewBtn) {

//         closeViewBtn.addEventListener("click", function () {

//             if (viewModal) {
//                 viewModal.classList.remove("active");
//             }

//         });

//     }


//     /* =====================================================
//        CLOSE EDIT MODAL
//     ===================================================== */

//     if (closeEditBtn) {

//         closeEditBtn.addEventListener("click", function () {

//             if (editModal) {
//                 editModal.classList.remove("active");
//             }

//         });

//     }


//     /* =====================================================
//        CANCEL DELETE
//     ===================================================== */

//     if (cancelDeleteBtn) {

//         cancelDeleteBtn.addEventListener("click", function () {

//             if (deleteModal) {
//                 deleteModal.classList.remove("active");
//             }


//             selectedUserId = null;


//             if (deleteUserName) {

//                 deleteUserName.textContent =
//                     "this user";

//             }

//         });

//     }


//     /* =====================================================
//        CLOSE MODAL WHEN CLICKING OUTSIDE
//     ===================================================== */

//     if (viewModal) {

//         viewModal.addEventListener("click", function (event) {

//             if (event.target === viewModal) {

//                 viewModal.classList.remove("active");

//             }

//         });

//     }


//     if (editModal) {

//         editModal.addEventListener("click", function (event) {

//             if (event.target === editModal) {

//                 editModal.classList.remove("active");

//             }

//         });

//     }


//     if (deleteModal) {

//         deleteModal.addEventListener("click", function (event) {

//             if (event.target === deleteModal) {

//                 deleteModal.classList.remove("active");

//                 selectedUserId = null;


//                 if (deleteUserName) {

//                     deleteUserName.textContent =
//                         "this user";

//                 }

//             }

//         });

//     }


//     /* =====================================================
//        ESC KEY CLOSE
//     ===================================================== */

//     document.addEventListener("keydown", function (event) {

//         if (event.key === "Escape") {


//             if (viewModal) {
//                 viewModal.classList.remove("active");
//             }


//             if (editModal) {
//                 editModal.classList.remove("active");
//             }


//             if (deleteModal) {
//                 deleteModal.classList.remove("active");
//             }


//             selectedUserId = null;


//             if (deleteUserName) {

//                 deleteUserName.textContent =
//                     "this user";

//             }

//         }

//     });

// });
document.addEventListener("DOMContentLoaded", function () {

    const byId = (id) => document.getElementById(id);

    const viewModal = byId("viewUserModal");
    const editModal = byId("editUserModal");
    const moderationModal = byId("moderationModal");
    const notification = byId("adminNotification");

    let toastTimer = null;


    // =====================================================
    // NOTIFICATION
    // =====================================================

    function showNotification(
        title,
        message,
        isError = false
    ) {
        if (!notification) {
            return;
        }

        byId("notificationTitle").textContent = title;
        byId("notificationMessage").textContent = message;

        const icon = notification.querySelector(
            ".notification-icon i"
        );

        if (icon) {
            icon.className = isError
                ? "fas fa-triangle-exclamation"
                : "fas fa-check";
        }

        notification.classList.toggle(
            "error",
            isError
        );

        notification.classList.add("show");

        clearTimeout(toastTimer);

        toastTimer = setTimeout(function () {
            notification.classList.remove("show");
        }, 4000);
    }


    // =====================================================
    // API REQUEST
    // =====================================================

    async function requestJson(
        url,
        options = {}
    ) {
        const response = await fetch(
            url,
            options
        );

        let result;

        try {
            result = await response.json();
        } catch (error) {
            throw new Error(
                "The server returned an invalid response."
            );
        }

        if (
            !response.ok
            || !result.success
        ) {
            throw new Error(
                result.message
                || "Unable to complete the request."
            );
        }

        return result;
    }


    // =====================================================
    // GET USER FROM TABLE ROW
    // =====================================================

    function getUser(userId) {

        const row = byId(
            "user-row-" + userId
        );

        if (!row) {
            return null;
        }

        return {
            row: row,

            id:
                row.dataset.userId,

            name:
                row.dataset.name || "",

            username:
                row.dataset.username || "",

            email:
                row.dataset.email || "",

            status: (
                row.dataset.status || "active"
            ).toLowerCase(),

            generated: Number(
                row.dataset.generated || 0
            ),

            humanized: Number(
                row.dataset.humanized || 0
            ),

            plagiarism: Number(
                row.dataset.plagiarism || 0
            ),

            seo: Number(
                row.dataset.seo || 0
            ),

            feedback: Number(
                row.dataset.feedback || 0
            ),

            total: Number(
                row.dataset.total || 0
            )
        };
    }


    function openModal(modal) {
        if (modal) {
            modal.classList.add("active");
        }
    }


    function closeModal(modal) {
        if (modal) {
            modal.classList.remove("active");
        }
    }


    // =====================================================
    // VIEW USER
    // =====================================================

    document
        .querySelectorAll(".view-btn")
        .forEach(function (button) {

            button.addEventListener(
                "click",
                function () {

                    const user = getUser(
                        this.dataset.userId
                    );

                    if (!user) {
                        showNotification(
                            "Error",
                            "User information was not found.",
                            true
                        );

                        return;
                    }

                    byId("viewName").textContent =
                        user.name || "No Name";

                    byId("viewUsername").textContent =
                        user.username
                            ? "@" + user.username
                            : "-";

                    byId("viewEmail").textContent =
                        user.email || "-";

                    byId("viewGenerated").textContent =
                        user.generated;

                    byId("viewHumanized").textContent =
                        user.humanized;

                    byId("viewPlagiarism").textContent =
                        user.plagiarism;

                    byId("viewSeo").textContent =
                        user.seo;

                    byId("viewFeedback").textContent =
                        user.feedback;

                    byId("viewTotalActivity").textContent =
                        user.total + " Total";

                    openModal(viewModal);
                }
            );
        });


    // =====================================================
    // OPEN EDIT USER
    // =====================================================

    document
        .querySelectorAll(".edit-btn")
        .forEach(function (button) {

            button.addEventListener(
                "click",
                function () {

                    const user = getUser(
                        this.dataset.userId
                    );

                    if (!user) {
                        showNotification(
                            "Error",
                            "User information was not found.",
                            true
                        );

                        return;
                    }

                    byId("editUserId").value =
                        user.id;

                    byId("editName").value =
                        user.name;

                    byId("editEmail").value =
                        user.email;

                    byId("editUsername").value =
                        user.username;

                    openModal(editModal);
                }
            );
        });


    // =====================================================
    // UPDATE USER
    // =====================================================

    const editForm = byId(
        "editUserForm"
    );

    if (editForm) {

        editForm.addEventListener(
            "submit",
            async function (event) {

                event.preventDefault();

                const userId =
                    byId("editUserId").value;

                const data = {
                    name:
                        byId("editName")
                            .value
                            .trim(),

                    email:
                        byId("editEmail")
                            .value
                            .trim(),

                    username:
                        byId("editUsername")
                            .value
                            .trim()
                };

                if (!data.name) {
                    showNotification(
                        "Error",
                        "Name is required.",
                        true
                    );

                    return;
                }

                const submitButton =
                    editForm.querySelector(
                        "button[type='submit']"
                    );

                submitButton.disabled = true;

                try {

                    const result =
                        await requestJson(
                            `/admin/users/${userId}/edit`,
                            {
                                method: "POST",

                                headers: {
                                    "Content-Type":
                                        "application/json"
                                },

                                body: JSON.stringify(data)
                            }
                        );

                    const user = getUser(userId);

                    if (user) {

                        user.row.dataset.name =
                            data.name;

                        user.row.dataset.username =
                            data.username;

                        const nameElement =
                            user.row.querySelector(
                                ".user-info strong"
                            );

                        if (nameElement) {
                            nameElement.textContent =
                                data.name;
                        }

                        let usernameElement =
                            user.row.querySelector(
                                ".user-info small"
                            );

                        if (data.username) {

                            if (!usernameElement) {

                                usernameElement =
                                    document.createElement(
                                        "small"
                                    );

                                user.row
                                    .querySelector(
                                        ".user-info"
                                    )
                                    .appendChild(
                                        usernameElement
                                    );
                            }

                            usernameElement.textContent =
                                "@" + data.username;

                        } else if (usernameElement) {

                            usernameElement.remove();
                        }
                    }

                    closeModal(editModal);

                    showNotification(
                        "Success",
                        result.message
                        || "User updated successfully."
                    );

                } catch (error) {

                    showNotification(
                        "Error",
                        error.message,
                        true
                    );

                } finally {

                    submitButton.disabled = false;
                }
            }
        );
    }


    // =====================================================
    // OPEN MODERATION MODAL
    // =====================================================

    document
        .querySelectorAll(".manage-btn")
        .forEach(function (button) {

            button.addEventListener(
                "click",
                function () {

                    const user = getUser(
                        this.dataset.userId
                    );

                    if (!user) {
                        showNotification(
                            "Error",
                            "User information was not found.",
                            true
                        );

                        return;
                    }

                    byId("moderationUserId").value =
                        user.id;

                    byId(
                        "moderationUserName"
                    ).textContent =
                        `${user.name || "User"} (${user.email})`;

                    byId("moderationAction").value =
                        "";

                    byId("moderationReason").value =
                        "";

                    openModal(moderationModal);
                }
            );
        });


    // =====================================================
    // APPLY MODERATION ACTION
    // =====================================================

    const moderationForm = byId(
        "moderationForm"
    );

    if (moderationForm) {

        moderationForm.addEventListener(
            "submit",
            async function (event) {

                event.preventDefault();

                const userId =
                    byId("moderationUserId").value;

                const action =
                    byId("moderationAction").value;

                const reason =
                    byId("moderationReason")
                        .value
                        .trim();

                const submitButton =
                    byId("submitModerationBtn");

                if (!action) {
                    showNotification(
                        "Error",
                        "Please choose an action.",
                        true
                    );

                    return;
                }

                if (reason.length < 10) {
                    showNotification(
                        "Error",
                        "Please enter a reason of at least 10 characters.",
                        true
                    );

                    return;
                }

                submitButton.disabled = true;

                submitButton.innerHTML =
                    '<i class="fas fa-spinner fa-spin"></i> Applying...';

                try {

                    const result =
                        await requestJson(
                            `/admin/users/${userId}/moderate`,
                            {
                                method: "POST",

                                headers: {
                                    "Content-Type":
                                        "application/json"
                                },

                                body: JSON.stringify({
                                    action: action,
                                    reason: reason
                                })
                            }
                        );

                    const user = getUser(userId);

                    if (user) {

                        user.row.dataset.status =
                            result.status;

                        const statusBadge =
                            user.row.querySelector(
                                ".status-badge"
                            );

                        if (statusBadge) {

                            statusBadge.className =
                                "status-badge status-"
                                + result.status;

                            statusBadge.textContent =
                                result.status.replaceAll(
                                    "_",
                                    " "
                                );
                        }
                    }

                    closeModal(
                        moderationModal
                    );

                    showNotification(
                        "Success",
                        result.message
                    );

                } catch (error) {

                    showNotification(
                        "Error",
                        error.message,
                        true
                    );

                } finally {

                    submitButton.disabled = false;

                    submitButton.innerHTML =
                        '<i class="fas fa-shield-halved"></i> Apply Action';
                }
            }
        );
    }


    // =====================================================
    // CLOSE BUTTONS
    // =====================================================

    const modalClosers = [
        [
            "closeViewBtn",
            viewModal
        ],
        [
            "closeEditBtn",
            editModal
        ],
        [
            "closeModerationBtn",
            moderationModal
        ]
    ];

    modalClosers.forEach(
        function (item) {

            const button =
                byId(item[0]);

            const modal =
                item[1];

            if (button) {
                button.addEventListener(
                    "click",
                    function () {
                        closeModal(modal);
                    }
                );
            }
        }
    );


    // =====================================================
    // OUTSIDE CLICK CLOSE
    // =====================================================

    [
        viewModal,
        editModal,
        moderationModal
    ].forEach(function (modal) {

        if (!modal) {
            return;
        }

        modal.addEventListener(
            "click",
            function (event) {

                if (event.target === modal) {
                    closeModal(modal);
                }
            }
        );
    });


    // =====================================================
    // ESCAPE KEY CLOSE
    // =====================================================

    document.addEventListener(
        "keydown",
        function (event) {

            if (event.key === "Escape") {

                closeModal(viewModal);
                closeModal(editModal);
                closeModal(
                    moderationModal
                );
            }
        }
    );


    // =====================================================
    // CLOSE NOTIFICATION
    // =====================================================

    const closeNotification =
        byId("closeNotification");

    if (closeNotification) {

        closeNotification.addEventListener(
            "click",
            function () {

                notification.classList.remove(
                    "show"
                );
            }
        );
    }

});