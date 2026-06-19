import os

# Carga variables desde un archivo .env si existe (solo en desarrollo).
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _normalize_db_url(url):
    # Supabase / Heroku a veces entregan "postgres://" pero SQLAlchemy
    # moderno requiere "postgresql://". Lo corregimos automáticamente.
    if url and url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class Config:
    # Clave para firmar los tokens JWT. EN PRODUCCIÓN ponla en una variable
    # de entorno SECRET_KEY (una cadena larga y aleatoria).
    SECRET_KEY = os.environ.get("SECRET_KEY", "cambia-esta-clave-secreta-en-produccion")

    # Cadena de conexión a la base de datos.
    # - Si DATABASE_URL no está definida, usamos SQLite (archivo local) para
    #   poder desarrollar y probar al instante, sin instalar nada.
    # - En Supabase / Railway / UCR solo cambias DATABASE_URL y todo funciona
    #   igual (migración sin tocar el código).
    SQLALCHEMY_DATABASE_URI = (
        _normalize_db_url(os.environ.get("DATABASE_URL")) or "sqlite:///raices.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Validez del token en horas. Decidimos un solo token de 24h.
    JWT_EXP_HOURS = int(os.environ.get("JWT_EXP_HOURS", "24"))
