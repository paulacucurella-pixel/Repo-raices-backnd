import os

from flask import Flask, request, jsonify
from flask_cors import CORS

from config import Config
from models import db, User, Point
from auth import generate_token, token_required

VALID_LINK_TYPES = {"person", "zone"}
VALID_ROLES = {"teacher", "student"}


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # CORS abierto para desarrollo (el frontend puede estar en otro dominio:
    # Wix, localhost, etc.). EN PRODUCCIÓN conviene restringir 'origins' a tu
    # dominio real en vez de "*".
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    db.init_app(app)
    with app.app_context():
        db.create_all()  # crea las tablas si no existen

    register_routes(app)
    return app


def register_routes(app):

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    # ---------------- Usuarios / autenticación ----------------

    @app.post("/api/users")
    def create_user():
        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        role = data.get("role") or "student"
        color = (data.get("color") or "#3388ff").strip()
        alias_note = (data.get("alias_note") or "").strip()

        if not name or not email or not password:
            return jsonify({"error": "name, email y password son obligatorios"}), 400
        if role not in VALID_ROLES:
            return jsonify({"error": "role debe ser 'teacher' o 'student'"}), 400
        if User.query.filter_by(email=email).first():
            return jsonify({"error": "Ese email ya está registrado"}), 409

        user = User(name=name, email=email, role=role, color=color, alias_note=alias_note)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        token = generate_token(user.id)
        return jsonify({"user": user.private_dict(), "token": token}), 201

    @app.post("/api/login")
    def login():
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            return jsonify({"error": "Credenciales inválidas"}), 401

        token = generate_token(user.id)
        return jsonify({"user": user.private_dict(), "token": token}), 200

    @app.get("/api/me")
    @token_required
    def me(current_user):
        return jsonify({"user": current_user.private_dict()}), 200

    @app.patch("/api/me/color")
    @token_required
    def update_color(current_user):
        data = request.get_json(silent=True) or {}
        color = (data.get("color") or "").strip()
        if not color:
            return jsonify({"error": "Falta el campo color"}), 400
        current_user.color = color
        db.session.commit()
        return jsonify({"user": current_user.private_dict()}), 200

    @app.patch("/api/me/name")
    @token_required
    def update_name(current_user):
        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "Falta el campo name"}), 400
        current_user.name = name
        if "alias_note" in data:
            current_user.alias_note = (data.get("alias_note") or "").strip()
        db.session.commit()
        return jsonify({"user": current_user.private_dict()}), 200

    @app.patch("/api/me/location")
    @token_required
    def update_location(current_user):
        data = request.get_json(silent=True) or {}
        try:
            lat = float(data["latitude"])
            lng = float(data["longitude"])
        except (KeyError, TypeError, ValueError):
            return jsonify(
                {"error": "latitude y longitude son obligatorios y numéricos"}
            ), 400
        current_user.center_lat = lat
        current_user.center_lng = lng
        db.session.commit()
        return jsonify({"user": current_user.private_dict()}), 200

    # ---------------- Puntos del mapa ----------------

    @app.get("/api/points")
    @token_required
    def list_points(current_user):
        # Todos los usuarios autenticados ven el mapa completo de la clase.
        points = Point.query.order_by(Point.created_at.asc()).all()
        return jsonify({"points": [p.to_dict() for p in points]}), 200

    @app.post("/api/points")
    @token_required
    def create_point(current_user):
        data = request.get_json(silent=True) or {}

        try:
            latitude = float(data["latitude"])
            longitude = float(data["longitude"])
        except (KeyError, TypeError, ValueError):
            return jsonify(
                {"error": "latitude y longitude son obligatorios y numéricos"}
            ), 400

        label = (data.get("label") or "").strip()
        if not label:
            return jsonify(
                {"error": "label (nombre de la persona o lugar) es obligatorio"}
            ), 400

        link_type = data.get("link_type") or "person"
        if link_type not in VALID_LINK_TYPES:
            return jsonify({"error": "link_type debe ser 'person' o 'zone'"}), 400

        point = Point(
            user_id=current_user.id,
            latitude=latitude,
            longitude=longitude,
            link_type=link_type,
            label=label,
            description=data.get("description") or "",
            notes=data.get("notes") or "",
            icon=data.get("icon") or "",
        )
        db.session.add(point)
        db.session.commit()
        return jsonify({"point": point.to_dict()}), 201

    @app.put("/api/points/<int:point_id>")
    @token_required
    def update_point(current_user, point_id):
        point = db.session.get(Point, point_id)
        if not point:
            return jsonify({"error": "Punto no encontrado"}), 404
        if point.user_id != current_user.id:
            return jsonify({"error": "Solo puedes editar tus propios puntos"}), 403

        data = request.get_json(silent=True) or {}

        if "latitude" in data:
            try:
                point.latitude = float(data["latitude"])
            except (TypeError, ValueError):
                return jsonify({"error": "latitude inválida"}), 400
        if "longitude" in data:
            try:
                point.longitude = float(data["longitude"])
            except (TypeError, ValueError):
                return jsonify({"error": "longitude inválida"}), 400
        if "link_type" in data:
            if data["link_type"] not in VALID_LINK_TYPES:
                return jsonify({"error": "link_type debe ser 'person' o 'zone'"}), 400
            point.link_type = data["link_type"]
        if "label" in data:
            label = (data["label"] or "").strip()
            if not label:
                return jsonify({"error": "label no puede quedar vacío"}), 400
            point.label = label
        if "description" in data:
            point.description = data["description"] or ""
        if "notes" in data:
            point.notes = data["notes"] or ""
        if "icon" in data:
            point.icon = data["icon"] or ""

        db.session.commit()
        return jsonify({"point": point.to_dict()}), 200

    @app.delete("/api/points/<int:point_id>")
    @token_required
    def delete_point(current_user, point_id):
        point = db.session.get(Point, point_id)
        if not point:
            return jsonify({"error": "Punto no encontrado"}), 404
        if point.user_id != current_user.id:
            return jsonify({"error": "Solo puedes eliminar tus propios puntos"}), 403
        db.session.delete(point)
        db.session.commit()
        return jsonify({"deleted": point_id}), 200


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
