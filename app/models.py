import bcrypt

from .database import db

# ============================================================
# USER MODEL
# ============================================================

class User(db.Model):

    __tablename__ = "users"

    # ========================================================
    # BASIC ACCOUNT INFORMATION
    # ========================================================

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=True
    )

    role = db.Column(
        db.String(20),
        nullable=True,
        default="user"
    )

    email = db.Column(
        db.String(255),
        unique=True,
        nullable=True
    )

    password = db.Column(
        db.String(255),
        nullable=True
    )

    username = db.Column(
        db.String(100),
        unique=True,
        nullable=True
    )

    

    profile_picture = db.Column(
        db.String(255),
        nullable=True
    )


    # ========================================================
    # EMAIL VERIFICATION
    # ========================================================

    is_verified = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    verification_code = db.Column(
        db.String(10),
        nullable=True
    )

    verification_expires = db.Column(
        db.DateTime,
        nullable=True
    )


    # ========================================================
    # PASSWORD RESET
    # ========================================================

    reset_token = db.Column(
        db.String(255),
        nullable=True
    )

    reset_expires = db.Column(
        db.DateTime,
        nullable=True
    )


    # ========================================================
    # USER SETTINGS
    # ========================================================

    default_content_type = db.Column(
        db.String(50),
        nullable=True,
        default="Blog"
    )

    default_word_count = db.Column(
        db.Integer,
        nullable=True,
        default=500
    )

    email_notifications = db.Column(
        db.Boolean,
        nullable=True,
        default=True
    )

    system_notifications = db.Column(
        db.Boolean,
        nullable=True,
        default=True
    )

    preferences = db.Column(
        db.Text,
        nullable=True
    )


    # ========================================================
    # ACCOUNT MODERATION
    # ========================================================

    status = db.Column(
        db.String(20),
        nullable=False,
        default="active"
    )
    suspended_until = db.Column(
    db.DateTime,
    nullable=True
     )
    generator_restricted_until = db.Column(db.DateTime, nullable=True)
    failed_login_attempts = db.Column(
    db.Integer,
    nullable=False,
    default=0
    )

    login_locked_until = db.Column(
    db.DateTime,
    nullable=True
    )
    admin_note = db.Column(
        db.Text,
        nullable=True
    )

    status_reason = db.Column(
        db.Text,
        nullable=True
    )

    status_changed_at = db.Column(
        db.DateTime,
        nullable=True
    )

    deletion_scheduled_at = db.Column(
        db.DateTime,
        nullable=True
    )


    # ========================================================
    # PASSWORD HASHING
    # ========================================================

    def set_password(self, password):

        if (
            not isinstance(password, str)
            or not password
        ):
            raise ValueError(
                "Password is required."
            )

        self.password = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

    # ========================================================
    # PASSWORD VERIFICATION
    # ========================================================

    def check_password(self, password):

        if (
            not isinstance(password, str)
            or not password
            or not self.password
        ):
            return False

        try:

            return bcrypt.checkpw(
                password.encode("utf-8"),
                self.password.encode("utf-8")
            )

        except (
            ValueError,
            TypeError,
            AttributeError
        ):

            return False


    # ========================================================
    # MODEL DISPLAY
    # ========================================================

    def __repr__(self):

        return (
            f"<User id={self.id} "
            f"email={self.email!r} "
            f"role={self.role!r} "
            f"status={self.status!r}>"
        )