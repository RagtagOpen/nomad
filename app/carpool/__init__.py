from flask import Blueprint

pool_bp = Blueprint('carpool', __name__)

from . import views
