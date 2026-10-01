from flask import render_template, session, redirect, url_for
from sqlalchemy import text

from app.database import db
from app.user.services.dashboard_service import get_dashboard_data


def dashboard_page():
    user_email = session.get("user_email")

    if not user_email:
        return redirect(url_for("auth.login"))

    # Existing dashboard data aur logic
    dashboard_data = get_dashboard_data(user_email)

    # Is user ke tamam plagiarism reports
    plagiarism_report_count = db.session.execute(
        text("""
            SELECT COUNT(*)
            FROM plagiarism_history
            WHERE user_email = :email
        """),
        {"email": user_email}
    ).scalar() or 0

    # Is user ke tamam SEO reports
    seo_report_count = db.session.execute(
        text("""
            SELECT COUNT(*)
            FROM seo_history
            WHERE user_email = :email
        """),
        {"email": user_email}
    ).scalar() or 0

    dashboard_data["plagiarism_report_count"] = plagiarism_report_count
    dashboard_data["seo_report_count"] = seo_report_count

    return render_template(
        "user/dashboard.html",
        **dashboard_data
    )