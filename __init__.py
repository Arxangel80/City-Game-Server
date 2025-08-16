import os

from dotenv import load_dotenv
from flask import Flask

from dashboard import dashboard as dashboard_blueprint
from test import test as test_blueprint
from user import user as user_blueprint

load_dotenv()


def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("FLASK_KEY")
    # app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DB_CONNECTION_STRING_CADMIN")
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///citygame.db' 
    # app.config["SQLALCHEMY_ECHO"] = True
    app.config["DEBUG"] = True
    # app.config["THREADED"] = True
    app.register_blueprint(dashboard_blueprint)
    app.register_blueprint(test_blueprint)
    app.register_blueprint(user_blueprint)

    return app
