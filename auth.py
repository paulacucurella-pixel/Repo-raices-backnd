from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import current_app, request, jsonify

from models import db, User


def generate_token(user_id):
    """Crea un token JWT firmado, válido por JWT_EXP_HOURS horas."""
    payload = {
        "sub": str(user_id),  # PyJWT requiere que 'sub' sea string
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc)
        + timedelta(hours=current_app.config["JWT_EXP_HOURS"]),
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def _get_token_from_header():
    # El cliente envía:  Authorization: Bearer <token>
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return None


def token_required(f):
    """Decorador para endpoints protegidos.

    Si el token es válido, pasa el usuario actual a la vista como
    'current_user'. Si no, responde 401.
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        token = _get_token_from_header()
        if not token:
            return jsonify({"error": "Falta el token de autenticación"}), 401

        try:
            payload = jwt.decode(
                token, current_app.config["SECRET_KEY"], algorithms=["HS256"]
            )
            user_id = int(payload["sub"])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "El token expiró, inicia sesión de nuevo"}), 401
        except (jwt.InvalidTokenError, KeyError, ValueError):
            return jsonify({"error": "Token inválido"}), 401

        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 401

        return f(*args, current_user=user, **kwargs)

    return decorated
