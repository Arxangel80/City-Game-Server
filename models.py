from datetime import datetime
import enum
from typing import Annotated
from flask_login import UserMixin
from sqlalchemy import (
    TIMESTAMP,
    Column,
    ForeignKey,
    Identity,
    Integer,
    String,
    BOOLEAN,
    Text,
    func,
    Enum,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from database import db
from werkzeug.security import generate_password_hash, check_password_hash

oid = Annotated[
    int,
    mapped_column(
        Integer,
        Identity(always=True, start=1),
        primary_key=True,
    ),
]


class Status(enum.Enum):
    IN_PROGRESS = enum.auto()
    COMPLETED = enum.auto()


class Role(enum.Enum):
    ADMIN = enum.auto()
    MODERATOR = enum.auto()
    USER = enum.auto()


class GameTypeEnum(enum.Enum):
    CAMPUSGAME = enum.auto()


class TaskType(db.Model):
    __tablename__ = "task_types"

    id: Mapped[oid]
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    tasks = relationship("Task", back_populates="task_type")

    def __init__(self, name, description):
        self.name = name
        self.description = description


class GameType(db.Model):
    __tablename__ = "game_types"

    id: Mapped[oid]
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    tasks_types = relationship("GameTypeTask", back_populates="game_type")
    sessions = relationship("Session", back_populates="game_type")

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def __repr__(self):
        return f"<GameType(name={self.name}, description={self.description})>"


class GameTypeTask(db.Model):
    __tablename__ = "game_type_tasks"

    id: Mapped[oid]
    game_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("game_types.id"), nullable=False
    )
    task_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("task_types.id"), nullable=False
    )
    game_type = relationship(
        "GameType", back_populates="tasks_types", foreign_keys=[game_type_id]
    )
    task_type = relationship("TaskType", foreign_keys=[task_type_id])

    def __repr__(self):
        return (
            f"<GameTypeTask(id={self.id}, game_type_name={self.game_type_name}, "
            f"task_type_name={self.task_type_name})>"
        )

    def __init__(self, game_type_id: int, task_type_id: int):
        self.game_type_id = game_type_id
        self.task_type_id = task_type_id


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[oid]
    username: Mapped[str] = mapped_column(String(25), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(25), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role), nullable=False, default=Role.USER)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=True, onupdate=func.now()
    )

    sessions_hosted = relationship("Session", back_populates="host_user")
    participants = relationship("SessionParticipant", back_populates="user")
    messages_sent = relationship(
        "ChatMessage",
        back_populates="user_sender",
        foreign_keys="ChatMessage.sender_id",
    )

    def __init__(
        self, username: str, email: str, password: str, role: Role = Role.USER
    ):
        self.username = username
        self.email = email
        self.role = role
        self.set_password(password)

    def is_admin(self):
        return self.role == Role.ADMIN

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}', role={self.role})>"


class Session(db.Model):
    __tablename__ = "sessions"

    id: Mapped[oid]
    host_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    status: Mapped[Status] = mapped_column(
        Enum(Status), nullable=False, default=Status.IN_PROGRESS
    )
    game_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("game_types.id"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=True, onupdate=func.now()
    )

    host_user = relationship("User", back_populates="sessions_hosted")
    participants = relationship("SessionParticipant", back_populates="session")
    messages = relationship("ChatMessage", back_populates="session")
    game_type = relationship("GameType", back_populates="sessions")
    tasks = relationship("Task", back_populates="session")

    def __repr__(self):
        return (
            f"<Session(id={self.id}, host_user_id={self.host_user_id}, "
            f"status={self.status.name if self.status is not None else None}, started_at={self.started_at}, "
            f"finished_at={self.finished_at})>"
        )

    def __init__(self, host_user_id: int, game_type_id: int):
        self.host_user_id = host_user_id
        self.game_type_id = game_type_id

    @classmethod
    def create_new_session(cls, host_user_id, db_session, game_type_name: GameTypeEnum):
        game_type_id = (
            db_session.query(GameType)
            .filter(GameType.name == game_type_name.name)
            .one()
            .id
        )
        new_session = cls(host_user_id=host_user_id, game_type_id=game_type_id)
        db_session.add(new_session)
        db_session.flush()

        participant = SessionParticipant(
            session_id=new_session.id, user_id=host_user_id
        )
        db_session.add(participant)
        task_types = (
            db_session.query(GameTypeTask).filter_by(game_type_id=game_type_id).all()
        )

        for game_type_task in task_types:
            task = Task(session_id=new_session.id, task_type_id=game_type_task.id)
            db_session.add(task)

        db_session.commit()
        return new_session


class SessionParticipant(db.Model):
    __tablename__ = "session_participants"

    id: Mapped[oid]
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sessions.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    joined_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, default=func.now(), nullable=False
    )

    session = relationship("Session", back_populates="participants")
    user = relationship("User", back_populates="participants")

    def __init__(self, session_id, user_id):
        self.session_id = session_id
        self.user_id = user_id


class Task(db.Model):
    __tablename__ = "tasks"

    id: Mapped[oid]
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sessions.id"), nullable=False
    )
    task_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("task_types.id"), nullable=False
    )
    status: Mapped[Status] = mapped_column(
        Enum(Status), nullable=False, default=Status.IN_PROGRESS
    )

    session = relationship("Session", back_populates="tasks")
    task_type = relationship("TaskType", back_populates="tasks")

    def __init__(
        self, session_id: int, task_type_id: int, status: Status = Status.IN_PROGRESS
    ):
        self.session_id = session_id
        self.task_type_id = task_type_id
        self.status = status


class ChatMessage(db.Model):
    __tablename__ = "chat_messages"

    id: Mapped[oid]
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sessions.id"), nullable=False
    )

    sender_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(TIMESTAMP, default=func.now())

    session = relationship("Session", back_populates="messages")
    user_sender = relationship(
        "User", back_populates="messages_sent", foreign_keys=[sender_id]
    )

    def __init__(self, session_id, sender_id, message):
        self.session_id = session_id
        self.sender_id = sender_id
        self.message = message
