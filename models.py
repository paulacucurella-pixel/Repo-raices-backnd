from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    """Profesora o estudiante.

    Nota: el color único de cada usuario lo guardamos como una columna aquí
    (relación 1 a 1) en vez de una tabla aparte. Para un color por persona es
    más simple y más rápido; si en el futuro quisieras varios colores por
    usuario, ahí sí convendría separarlo en su propia tabla.
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")  # 'teacher' | 'student'
    color = db.Column(db.String(7), nullable=False, default="#3388ff")  # color del usuario (hex)
    center_lat = db.Column(db.Float, nullable=True)   # ubicación del usuario (su "centro")
    center_lng = db.Column(db.Float, nullable=True)
    alias_note = db.Column(db.String(280), default="")  # explicación de su alias (de dónde viene)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Si se borra un usuario, se borran sus puntos.
    points = db.relationship(
        "Point", backref="user", cascade="all, delete-orphan", lazy=True
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def public_dict(self):
        # Datos seguros para mostrar a toda la clase (sin email ni contraseña).
        # Pensado para proteger la privacidad del alumnado.
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "color": self.color,
            "center_lat": self.center_lat,
            "center_lng": self.center_lng,
            "alias_note": self.alias_note or "",
        }

    def private_dict(self):
        # Datos completos, solo para el propio usuario autenticado.
        d = self.public_dict()
        d["email"] = self.email
        d["created_at"] = self.created_at.isoformat() if self.created_at else None
        return d


class Point(db.Model):
    """Un punto en el mapa: una persona o un vínculo con una zona."""

    __tablename__ = "points"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    link_type = db.Column(db.String(20), nullable=False, default="person")  # 'person' | 'zone'
    label = db.Column(db.String(160), nullable=False)   # nombre de la persona o del lugar
    description = db.Column(db.Text, default="")         # párrafo breve sobre el vínculo
    notes = db.Column(db.Text, default="")               # leyenda / notas adicionales
    icon = db.Column(db.String(80), default="")          # ícono elegido por el usuario
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self, include_owner=True):
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "link_type": self.link_type,
            "label": self.label,
            "description": self.description or "",
            "notes": self.notes or "",
            "icon": self.icon or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_owner and self.user:
            # Incluimos el color y nombre del dueño para pintarlo en el mapa.
            data["owner"] = self.user.public_dict()
        return data
