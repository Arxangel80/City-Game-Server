from flask_login import LoginManager

import os

from flask_socketio import emit, join_room

from models import (
    GameType,
    Role,
    Task,
    TaskType,
    GameTypeTask,
    User,
    Status,
    Session,
    SessionParticipant,
    ChatMessage,
)

from database import db
from user import active_users

from werkzeug.security import generate_password_hash
import random

from __init__ import create_app
from sio import sio
from util import get_random_coordinates, printc


app = create_app()

sio.init_app(app)
db.init_app(app)


login_manager = LoginManager()
login_manager.login_view = "dashboard.login_page"
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# Seed database with initial data
def seed_initial_data():
    admin = User(
        username=os.getenv("ADMIN_USERNAME"),
        password=os.getenv("ADMIN_PASSWORD"),
        email="Admin1@cgame.com",
        role=Role.ADMIN,
    )
    db.session.add(admin)
    CAMPUSGAME_TASKS_TYPES = [
        TaskType(name="NFC", description="Read NFC tag."),
        TaskType(name="Gesture", description="Show a victory gesture."),
        TaskType(name="AR", description="Locate and retrieve hidden objects."),
        TaskType(name="Grill", description="Read the message."),
        TaskType(name="Cipher", description="Decipher code."),
    ]

    db.session.add_all(CAMPUSGAME_TASKS_TYPES)
    db.session.flush()

    campus_game = GameType(name="CAMPUSGAME", description="Politechnika campus quest.")
    db.session.add(campus_game)
    db.session.flush()

    for task_type in CAMPUSGAME_TASKS_TYPES:
        game_type_task = GameTypeTask(
            game_type_id=campus_game.id, task_type_id=task_type.id
        )
        db.session.add(game_type_task)
    db.session.commit()


# Create dummy entities for debugging purposes
def create_dummy_entities(users_nr, sessions_nr, max_session_participants, msgs_number):
    if (
        users_nr < sessions_nr
        or users_nr <= 0
        or sessions_nr <= 0
        or max_session_participants <= 0
    ):
        raise ValueError("Users number should be bigger than sessions number and not 0")

    # Generate dummy users entities in database
    users_list = []
    for i in range(1, users_nr + 1):
        user = User(
            username=f"User{i}",
            email=f"user{i}@example.com",
            password=f"password{i}",
        )
        users_list.append(user)
    db.session.add_all(users_list)
    db.session.flush()

    users_list = users_list[1:]  # Don't treat the admin as a user

    campus_game = GameType.query.filter(GameType.name == "CAMPUSGAME").one()

    # Generate dummy sessions entities in database
    user_ids = [user.id for user in users_list]
    sessions_list = []
    for i in range(sessions_nr):
        # Use modulo to cycle through user_ids if more sessions than users
        host_id = user_ids[i % len(user_ids)] if i != sessions_nr - 1 else user_ids[0]
        session = Session(host_user_id=host_id, game_type_id=campus_game.id)
        sessions_list.append(session)
    db.session.add_all(sessions_list)
    db.session.flush()

    session_participants_list = []
    user_index = 0
    user_counter = max_session_participants
    for session in sessions_list:
        for i in range(user_counter):
            user_index = (user_index + 1) % len(users_list)
            participant = SessionParticipant(
                session_id=session.id, user_id=users_list[user_index].id
            )
            session_participants_list.append(participant)
        user_counter -= 1
        if user_counter == 0:
            user_counter = max_session_participants
    db.session.add_all(session_participants_list)
    db.session.flush()

    campus_tasks_types = TaskType.query.all()

    # Generate dummy tasks entities in database
    tasks_list = []
    for session in sessions_list:
        for tasktype in campus_tasks_types:
            task = Task(
                session_id=session.id,
                task_type_id=tasktype.id,
                status=(
                    Status.COMPLETED
                    if random.randrange(2) % 2 == 0
                    else Status.IN_PROGRESS
                ),
            )
            tasks_list.append(task)
    db.session.add_all(tasks_list)
    db.session.flush()

    admin = User.query.filter(User.role == Role.ADMIN).one()

    # Generate dummy messages entities in database
    message1 = ChatMessage(
        session_id=sessions_list[0].id,
        sender_id=admin.id,
        message="Hello, this is a test message!",
    )
    message2 = ChatMessage(
        session_id=sessions_list[0].id,
        sender_id=users_list[0].id,
        message="Hello, admin!",
    )
    message3 = ChatMessage(
        session_id=sessions_list[0].id,
        sender_id=admin.id,
        message="Hello, user!",
    )
    db.session.add_all([message1, message2, message3])

    for i in range(msgs_number):
        sender_type = random.choice(["user", "admin"])
        msg = ChatMessage(
            session_id=random.choice(sessions_list[1:-1]).id,
            sender_id=(
                admin.id
                if sender_type == Role.ADMIN
                else random.choice(users_list[1:-1]).id
            ),
            message="T" * int((random.random() * 1000)),
        )
        db.session.add(msg)

    db.session.commit()

    last_session = db.session.query(Session).order_by(Session.id.desc()).first()
    last_session.status = Status.COMPLETED
    db.session.commit()


with app.app_context():
    db.drop_all()
    db.create_all()
    # create_dummy_entities(12, 5, 4, 25)
    seed_initial_data()


# Routes for debug purposes
@app.route("/drop")
def drop():
    db.drop_all()
    return "Dropped"


@app.route("/create")
def create():
    db.create_all()
    seed_initial_data()
    return "Created"


@app.route("/seed")
def seed():
    seed_initial_data()
    return "Seeded"


@app.route("/createDummy")
def createDummy():
    create_dummy_entities(12, 5, 4, 25)
    return "Created"


@app.route("/createAll")
def createAll():
    db.create_all()
    create_dummy_entities(12, 5, 4, 25)
    return "Created"
 

@app.route("/active_users")
def show_active_users():
    return [user.to_dict() for user in active_users]


@app.route("/random_task")
def random_task():
    tasks = db.session.query(Task).all()
    for task in tasks:
        task.status = (
            Status.COMPLETED if random.randrange(2) % 2 == 0 else Status.IN_PROGRESS
        )
    db.session.commit()
    return "Randomed"


if __name__ == "__main__":
    sio.run(app, debug=True, host="192.168.0.13")
