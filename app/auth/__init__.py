from flask import Blueprint

bp = Blueprint("auth_bp", __name__)

from app.auth import routes