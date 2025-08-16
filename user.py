from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_socketio import emit, join_room, disconnect
from sqlalchemy import or_
from werkzeug.security import check_password_hash

from database import db
from sio import sio
from models import (
    ChatMessage,
    GameTypeEnum,
    Session,
    Status,
    User,
    SessionParticipant,
)
from util import printc

user = Blueprint("user", __name__)


class Active_user:
    def __init__(self, user_id, session_id=None, longitude=None, latitude=None):
        self.user_id = user_id
        self.session_id = session_id
        self.latitude = longitude
        self.longitude = latitude

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "longitude": self.longitude,
            "latitude": self.latitude,
        }


# TODO Should be dict
active_users = []


@user.route("/users/login", methods=["POST"])
def user_login():
    # For mobile app, we expect JSON data
    if request.is_json:
        data = request.get_json()
        username = data.get("name")
        password = data.get("password")
    # For web form, we expect form data
    else:
        username = request.form["name"]
        password = request.form["password"]
    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        login_user(user)
        return jsonify({"status": "success", "message": "Logged in successfully"})
    else:
        return jsonify({"status": "error", "message": "Invalid credentials"}), 401


@user.route("/signup", methods=["POST"])
def signup():
    username = request.form.get("name")
    email = request.form.get("email")
    password = request.form.get("password")
    if not username or not email or not password:
        flash("All fields are required!")
        return redirect(url_for("test.test_page"))

    existing_user = User.query.filter(
        or_(User.email == email, User.username == username)
    ).one_or_none()

    if existing_user:
        if existing_user.email == email:
            printc("here")
            flash("Email already registered!")
        elif existing_user.username == username:
            printc("Or here")
            flash("Username already registered!")
        return redirect(url_for("test.test_page"))

    new_user = User(username=username, email=email, password=password)
    db.session.add(new_user)
    db.session.commit()

    flash(
        f"Account created successfully! Username: {new_user.username}, id: {new_user.id}"
    )
    return redirect(url_for("test.test_page"))


@user.route("/sessions/join", methods=["POST"])
def join_session():
    if not current_user.is_authenticated:
        flash("You need to login first")
        return redirect(url_for("test.test_page"))

    session_id = request.form.get("session_id")

    session = Session.query.filter(Session.id == session_id).one_or_none()
    sessionParticipants = session.participants
    printc(sessionParticipants)

    if not session:
        flash("Sesion not found")
        return redirect(url_for("test.test_page"))

    is_participant = any(
        participant.user_id == current_user.id for participant in session.participants
    )
    if is_participant:
        flash("Current user already participate in this session")
        return redirect(url_for("test.test_page"))

    session_participant = SessionParticipant(session_id, current_user.id)
    db.session.add(session_participant)
    db.session.commit()

    username = current_user.username

    flash(f"User {username} joined session {session_id}", "success")

    sio.emit("SessionUpdated", {"username": username, "session_id": session_id})
    return redirect(url_for("user.user_login_get"))


@sio.on("connect")
def handle_connect():
    if not current_user.is_authenticated:
        return False
    printc(f"Client {current_user} connected")
    active_users.append(Active_user(user_id=current_user.id))
    
    emit("connected", {"message": "Connected to the server wia SocketIO!"})


@sio.on("disconnect")
def handle_disconnect():
    user_id = current_user.id

    index_to_remove = None
    for i, user in enumerate(active_users):
        if user.user_id == user_id:
            index_to_remove = i
            break

    if index_to_remove is not None:
        active_users.pop(index_to_remove)
    printc("Client disconnected")


@sio.on("messageSended")
def handle_message(message):
    if not current_user.is_authenticated:
        emit("Alert", {"message": "You need to log in first."})
        return

    user_id = current_user.id

    user_session = (
        db.session.query(Session.id)
        .join(Session.participants)
        .filter(SessionParticipant.user_id == user_id)
        .one_or_none()
    )
    message = ChatMessage(session_id=user_session, sender_id=user_id, message=message)
    db.session.add(message)
    db.session.commit()
    sio.emit("response", {"message": "Message received!"})


@sio.on("sessionUpdate")
def handle_session_update():
    if not current_user.is_authenticated:
        emit("Alert", {"message": "You need to log in first."})
        return False

    user_id = current_user.id

    user_sessions = Session.query.filter(
        (Session.host_user_id == user_id) & (Session.status == Status.IN_PROGRESS)
    ).all()

    if len(user_sessions) > 1:
        emit("Alert", {"message": "You already have an active session."})
        return

    new_session = Session.create_new_session(
        host_user_id=user_id,
        db_session=db.session,
        game_type_name=GameTypeEnum.CAMPUSGAME,
    )
    db.session.add(new_session)
    db.session.commit()

    session_data = {
        "id": new_session.id,
        "host_name": new_session.host_user.username,
        "progress": new_session.status.name,
    }
    printc("Session created: " + str(new_session))
    emit("sessionCreated", session_data)


@sio.on("request_tasks")
def handle_task_request(session_id):
    session = db.session.query(Session).filter(Session.id == session_id).first()
    if session:
        tasks_data = [
            {
                "name": task.task_type,
                "description": task.task_type,
                "status": task.status,
                "id": task.id,
            }
            for task in session.tasks
        ]
        emit("tasks_update", {"tasks": tasks_data})
    else:
        emit("tasks_update", {"error": "Session not found"})


@sio.on("coordinatesUpdate")
def handle_coordinates_update(data):
    for user in active_users:
        if user.user_id == int(data["user_id"]):
            user.longitude = float(data["longitude"])
            user.latitude = float(data["latitude"])
            emit("updatedUserCoordinates", active_users)
            break


@user.route("/user/logout", methods=["POST"])
def user_logout():
    if current_user.is_authenticated:
        logout_user()
        return redirect(url_for("test.test_page"))
    else:
        flash("You are not logged in")
        return redirect(url_for("test.test_page"))
