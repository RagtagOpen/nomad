from flask import Blueprint

dest_bp = Blueprint('destination', __name__)

from . import views
