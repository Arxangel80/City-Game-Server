from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_socketio import emit, join_room
from werkzeug.security import check_password_hash

from database import db
from models import ChatMessage, Role, Session, Status, Task, User
from sio import sio
from util import printc

from user import active_users

dashboard = Blueprint("dashboard", __name__)


@dashboard.route("/")
def index():
    return redirect(url_for("dashboard.login_page"))


@dashboard.route("/admin", methods=["GET"])
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard_page"))
    return render_template("dashboard_login.html")


@dashboard.route("/login", methods=["POST"])
def admin_login():
    username = request.form.get("username")
    password = request.form.get("password")
    remember = True if request.form.get("remember") else False
    user = db.session.query(User).filter(User.username == username).first()

    if not user or not user.check_password(password):
        flash("Please check your login details and try again.")
        return redirect(url_for("dashboard.login_page"))

    if not user.is_admin():
        flash("This page alloved only for admins.")
        return redirect(url_for("dashboard.login_page"))

    login_user(user, remember=remember)

    return redirect(url_for("dashboard.dashboard_page"))


@dashboard.route("/dashboard", methods=["GET"])
@login_required
def dashboard_page():
    if not current_user.is_admin():
        return redirect(url_for("dashboard.login_page"))
    return render_template(
        "dashboard.html", sessions=get_sessions_data(), active_users=active_users
    )


@dashboard.route("/api/active_users", methods=["GET"])
@login_required
def api_active_users():
    if not current_user.is_admin():
        return redirect(url_for("dashboard.login_page"))

    active_users_data = [user.to_dict() for user in active_users]
    return jsonify({"active_users": active_users_data})


def get_sessions_data():
    active_sessions = (
        db.session.query(Session).filter(Session.status == Status.IN_PROGRESS).all()
    )
    sessions_data = []
    for session in active_sessions:
        tasks = session.tasks
        tasks_count = len(tasks)
        pending_tasks_count = sum(1 for t in tasks if t.status == Status.IN_PROGRESS)
        progress = f"{pending_tasks_count}/{tasks_count}"

        sessions_data.append(
            {
                "id": session.id,
                "host_name": str(session.host_user.username),
                "progress": progress,
            }
        )
    return sessions_data


@dashboard.route("/api/sessions/<session_id>/tasks", methods=["GET"])
@login_required
def get_session_tasks(session_id):
    if not current_user.is_admin():
        return redirect(url_for("dashboard.login_page"))
    session = db.session.query(Session).filter(Session.id == session_id).first()

    if not session:
        flash("Session not found")
        return redirect(url_for("dashboard.dashboard"))

    tasks_data = []
    for task in session.tasks:
        tasks_data.append(
            {
                "name": task.task_type.name,
                "description": task.task_type.description,
                "status": task.status.name,
                "id": task.id,
            }
        )
    return tasks_data


@dashboard.route("/api/tasks/<id>/complete", methods=["PATCH"])
@login_required
def complete_task(id):
    if not current_user.is_admin():
        return redirect(url_for("dashboard.login_page"))
    task = db.session.query(Task).filter(Task.id == id).one()
    task.status = Status.COMPLETED
    db.session.commit()
    return jsonify({"message": "Task completed successfully"}), 200


@sio.on("getSessionUsersCoordinates")
def get_Session_Users_Coordinates(data):
    printc(data)
    session_id = data.get("session_id")
    printc(session_id)

    if not session_id:
        return {"error": "Session ID is required"}

    session = db.session.query(Session).filter(Session.id == session_id).one_or_none()

    if session is None:
        return {"error": "Session not found"}

    user_ids = [user.id for user in session.participants]

    users_to_send = [user for user in active_users if user.id in user_ids]

    user_data = [user.to_dict() for user in users_to_send]

    printc(user_data)
    emit("sessionUsersCoordinatesResponse", {"user_data": user_data})


@dashboard.route("/admin/logout", methods=["POST"])
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for("dashboard.login_page"))
