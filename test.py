from flask import Blueprint, render_template
from flask_login import current_user

from sio import sio

from util import printc

test = Blueprint("test", __name__)

from user import active_users


@test.route("/test", methods=["GET"])
def test_page():
    if current_user.is_authenticated:
        return render_template(
            "test.html",
            user=str(current_user),
            active_users=[user.to_dict() for user in active_users],
        )
    else:
        return render_template("test.html")


@sio.on("disconnect")
def handle_disconnect():
    printc("Client disconnected")
