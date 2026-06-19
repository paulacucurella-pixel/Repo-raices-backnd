# Raíces — Backend (API)

API en Flask para una app de mapas colaborativos donde cada usuario marca sus
orígenes y vínculos familiares en el mundo hispanohablante. Cada persona tiene
un **color único** (su centro), marca **puntos** (una persona o un vínculo con
una zona), y **toda la clase ve el mapa completo** y sincronizado.

Esta API guarda los datos y controla el acceso. El mapa interactivo (frontend)
se conecta a ella. Está pensada para desarrollarse en una plataforma gratuita
(Supabase / Railway / Render) y luego **migrar a la infraestructura de UCR sin
cambiar el código** (solo cambias `DATABASE_URL`).

## Estructura

| Archivo            | Qué hace                                                |
|--------------------|---------------------------------------------------------|
| `app.py`           | Aplicación Flask y todos los endpoints                  |
| `models.py`        | Tablas de la base de datos: `User` y `Point`            |
| `auth.py`          | Tokens JWT y protección de endpoints                    |
| `config.py`        | Clave secreta, conexión a BD, expiración del token      |
| `requirements.txt` | Dependencias                                            |
| `.env.example`     | Plantilla de variables de entorno                       |

## Cómo correrlo localmente

```bash
python3 -m venv venv
source venv/bin/activate          # En Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # opcional para desarrollo
python app.py
```

La API queda en `http://localhost:5000`. Sin `DATABASE_URL`, usa SQLite (crea
un archivo en `instance/raices.db`), así puedes probar sin instalar PostgreSQL.

## Probar rápido con curl

```bash
# 1. Crear la profesora (te devuelve un token)
curl -X POST http://localhost:5000/api/users \
  -H "Content-Type: application/json" \
  -d '{"name":"Prof. Paula","email":"paula@ucr.edu","password":"secreto123","role":"teacher","color":"#e6194b"}'

# 2. Guarda el token que recibiste y úsalo en las llamadas protegidas:
TOKEN="pega-aqui-el-token"

# 3. Crear un punto
curl -X POST http://localhost:5000/api/points \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"latitude":19.4326,"longitude":-99.1332,"link_type":"person","label":"Abuela Rosa","description":"Nació en CDMX.","notes":"Lado materno.","icon":"star"}'

# 4. Ver todos los puntos de la clase
curl http://localhost:5000/api/points -H "Authorization: Bearer $TOKEN"
```

## Endpoints

| Método | Ruta                    | Protegido | Descripción                              |
|--------|-------------------------|-----------|------------------------------------------|
| POST   | `/api/users`            | No        | Registrar usuario (devuelve token)       |
| POST   | `/api/login`            | No        | Iniciar sesión (devuelve token)          |
| GET    | `/api/me`               | Sí        | Datos del usuario actual                 |
| PATCH  | `/api/me/color`         | Sí        | Cambiar el color propio                  |
| PATCH  | `/api/me/location`      | Sí        | Fijar la ubicación (centro) del usuario  |
| GET    | `/api/points`           | Sí        | Todos los puntos de la clase             |
| POST   | `/api/points`           | Sí        | Crear un punto                           |
| PUT    | `/api/points/<id>`      | Sí        | Editar un punto **propio**               |
| DELETE | `/api/points/<id>`      | Sí        | Eliminar un punto **propio**             |
| GET    | `/api/health`           | No        | Comprobar que la API está viva           |

Las rutas protegidas requieren el header `Authorization: Bearer <token>`.

## Privacidad (importante para el alumnado)

- Las contraseñas se guardan **encriptadas** (hash), nunca en texto plano.
- El listado público de puntos (`/api/points`) muestra el nombre y color del
  dueño, pero **nunca su email ni su contraseña**.
- Solo el dueño de un punto puede editarlo o borrarlo.
- En producción, cambia el `origins: "*"` de CORS (en `app.py`) por tu dominio
  real, y pon una `SECRET_KEY` larga y secreta.

## Desplegar en una plataforma gratuita (fase de desarrollo)

En **Render** o **Railway**, conecta tu repositorio de GitHub y define:
- Variable `SECRET_KEY` (genera una con `python -c "import secrets; print(secrets.token_hex(32))"`)
- Variable `DATABASE_URL` con tu PostgreSQL (Supabase o el de la plataforma)
- Comando de arranque: `gunicorn app:app`

## Migrar a UCR más adelante

Como usamos SQLAlchemy, **no hay que reescribir nada**: cuando tengas el
servidor o la base de datos de UCR (ITS / Developer Portal), solo cambias la
variable `DATABASE_URL` por la nueva conexión PostgreSQL y vuelves a desplegar.

## Nota sobre el esquema

El color de cada usuario está como una columna en la tabla `users` (un color
por persona, relación 1 a 1), en lugar de una tabla aparte. Es más simple y
rápido; si en el futuro quisieras varios colores por usuario, ahí convendría
separarlo en su propia tabla.

La ubicación del usuario (su "centro") se guarda en las columnas `center_lat` y
`center_lng` de la tabla `users`. El listado de puntos incluye, dentro de cada
`owner`, esos valores, para poder trazar las líneas desde el centro de cada
persona hacia sus puntos.

> Si ya habías creado la base de datos antes de este cambio de esquema, borra el
> archivo `instance/raices.db` (o recrea la base en PostgreSQL) para que se
> generen las nuevas columnas. En producción real, lo apropiado es usar
> migraciones (por ejemplo, Flask-Migrate / Alembic).
