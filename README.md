# 🏆 Digital Sports DMC — Plataforma de Gestión Deportiva Escolar

> **Proyecto Formativo — Ficha / Código: 3215869**  
> **Institución Educativa Distrital Diego Montaña Cuéllar (DMC)**

Plataforma web integral para la administración, seguimiento y difusión de torneos deportivos escolares (fútbol, microfútbol, torneos interclases e interroscas). Facilita el control de inscripciones, conformación de equipos por docentes, programación de encuentros, actas de juego en tiempo real, tablas de posiciones automáticas, estadísticas de goleadores y amonestaciones, así como un portal de noticias institucionales.

---

## 📌 Tabla de Contenidos

- [Características Principales](#-características-principales)
- [Stack Tecnológico](#-stack-tecnológico)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Requisitos Previos](#-requisitos-previos)
- [Guía de Instalación y Puesta en Marcha](#-guía-de-instalación-y-puesta-en-marcha)
  - [1. Iniciar Base de Datos (XAMPP / MySQL)](#1-iniciar-base-de-datos-xampp--mysql)
  - [2. Configurar el Entorno Virtual de Python](#2-configurar-el-entorno-virtual-de-python)
  - [3. Instalar Dependencias del Backend](#3-instalar-dependencias-del-backend)
  - [4. Configurar Variables de Entorno (.env)](#4-configurar-variables-de-entorno-env)
  - [5. Inicializar la Base de Datos y Migraciones](#5-inicializar-la-base-de-datos-y-migraciones)
  - [6. Cargar Datos de Prueba (Opcional recomendado)](#6-cargar-datos-de-prueba-opcional-recomendado)
  - [7. Iniciar el Servidor Backend](#7-iniciar-el-servidor-backend)
  - [8. Abrir la Aplicación (Frontend)](#8-abrir-la-aplicación-frontend)
- [Cuentas de Acceso y Roles de Prueba](#-cuentas-de-acceso-y-roles-de-prueba)
- [Configuración de la API de Google (Google Sign-In)](#-configuración-de-la-api-de-google-google-sign-in)
- [Arquitectura del Sistema](#-arquitectura-del-sistema)
- [Referencia de la API REST](#-referencia-de-la-api-rest)
- [Pruebas Automatizadas (Testing)](#-pruebas-automatizadas-testing)
- [Solución de Problemas Frecuentes (FAQ)](#-solución-de-problemas-frecuentes-faq)

---

## ✨ Características Principales

- **Gestión de Torneos:** Creación de torneos por categorías (Masculino, Femenino, Interroscas), estados (planificación, activo, finalizado) y cálculo automático de puntuación.
- **Equipos y Plantillas:** Registro de equipos por parte de docentes tutores, vinculación de estudiantes con números de dorsal y validación de reglas de permanencia.
- **Calendario y Actas de Partido:** Programación de encuentros, registro de resultados, goles con minuto y tipo, amonestaciones (tarjetas amarillas y rojas).
- **Tablas de Posiciones Automáticas:** Cálculo dinámico de Partidos Jugados (PJ), Ganados (PG), Empatados (PE), Perdidos (PP), Goles a Favor (GF), Goles en Contra (GC), Diferencia de Goles (DG) y Puntos (PTS).
- **Tabla de Goleadores y Disciplina:** Ranking de máximos artilleros del campeonato y control de faltas disciplinarias.
- **Portal de Noticias y Comentarios:** Publicación de notas deportivas institucionales, subida de imágenes y comentarios moderados.
- **Centro de Notificaciones:** Alertas personalizadas para usuarios sobre cambios de partidos, resultados y anuncios.
- **Seguridad y Control de Acceso:** 
  - 4 roles bien diferenciados: **Administrador**, **Docente**, **Estudiante** y **Visitante**.
  - Autenticación mediante sesión segura (`HttpOnly`, `SameSite=Lax`), soporte opcional para **Google OAuth 2.0** y recuperación de contraseña vía token seguro.
  - Protección activa contra ataques **CSRF** e inyección **XSS**.
  - Módulo de auditoría que registra acciones administrativas críticas.

---

## 🛠 Stack Tecnológico

### Backend
- **Lenguaje:** Python 3.10+
- **Framework Web:** Flask 3.1.1
- **ORM / Base de Datos:** Flask-SQLAlchemy 3.1.1 con motor MySQL (PyMySQL)
- **CORS:** Flask-CORS
- **Variables de Entorno:** python-dotenv
- **Testing:** Pytest

### Frontend
- **Estructura y Vistas:** HTML5 semántico
- **Estilos:** Vanilla CSS3 moderno y modular con diseño oscuro, soporte responsivo y componentes Bootstrap 5.3 + Bootstrap Icons
- **Interactividad:** JavaScript moderno (ES6+ modular) con cliente API unificado (`api.js`), manejo de sesión y renderizado dinámico (`layout.js`)

### Infraestructura / Entorno Local
- **Base de Datos:** MySQL / MariaDB (vía XAMPP en puerto 3306)
- **Servidor Web:** Servidor integrado de Flask (o Live Server para desarrollo independiente del frontend)

---

## 📁 Estructura del Proyecto

```text
Digital Sports DMC_3215869/
│
├── Backend-Digital Sports/           # Servidor y API REST (Flask + SQLAlchemy)
│   ├── backend/
│   │   ├── controllers/              # Lógica de negocio de cada módulo (MVC - C)
│   │   │   ├── auth_controller.py
│   │   │   ├── torneo_controller.py
│   │   │   ├── equipo_controller.py
│   │   │   ├── partido_controller.py
│   │   │   └── ...
│   │   ├── models/                   # Definición de tablas y relaciones de BD (MVC - M)
│   │   │   ├── usuario.py
│   │   │   ├── estudiante.py
│   │   │   ├── docente.py
│   │   │   ├── torneo.py
│   │   │   ├── equipo.py
│   │   │   ├── partido.py
│   │   │   ├── gol.py
│   │   │   ├── falta.py
│   │   │   ├── noticia.py
│   │   │   └── auditoria.py
│   │   ├── routes/                   # Definición de rutas y mapeo a controladores
│   │   │   ├── __init__.py           # Blueprint raíz (/api)
│   │   │   ├── usuario_routes.py
│   │   │   ├── torneo_routes.py
│   │   │   └── ...
│   │   ├── services/                 # Servicios transversales (clasificación, auditoría, email)
│   │   ├── utils/                    # Funciones auxiliares (auth, CSRF, respuestas JSON, fechas)
│   │   ├── __init__.py               # Factory de la aplicación Flask (create_app)
│   │   ├── config.py                 # Entornos (Development, Production, Testing)
│   │   ├── datos_prueba.py           # Script generador de datos realistas para pruebas
│   │   ├── extensions.py             # Instancia compartida de SQLAlchemy
│   │   ├── migraciones.py            # Migraciones automáticas de esquema e idempotentes
│   │   └── requirements.txt          # Dependencias de Python
│   │
│   ├── tests/                        # Suite de pruebas automatizadas con Pytest
│   │   ├── conftest.py               # Fixtures y cliente HTTP de prueba (SQLite en memoria)
│   │   ├── test_auth.py
│   │   ├── test_equipos.py
│   │   ├── test_partidos_clasificacion.py
│   │   └── ...
│   │
│   ├── .env.example                  # Plantilla de variables de entorno
│   ├── .env                          # Variables de entorno locales (NO versionar valores reales)
│   └── run.py                        # Punto de entrada para ejecutar el backend Flask
│
├── Frontend-Digital Sports/          # Interfaz de usuario (HTML + CSS + Vanilla JS)
│   ├── assets/
│   │   ├── css/                      # Hojas de estilo modulares
│   │   │   ├── global.css            # Variables de tema, fuentes, layout base y reset
│   │   │   ├── panel.css             # Estilos de dashboards
│   │   │   ├── admin.css             # Estilos del módulo administrativo
│   │   │   └── ...
│   │   ├── img/                      # Logotipos, banners y recursos gráficos
│   │   └── js/
│   │       ├── core/
│   │       │   ├── api.js            # Cliente HTTP fetch, CSRF, spinners, toasts y errores
│   │       │   └── layout.js         # Navbar y Sidebar reactivos según rol del usuario
│   │       └── pages/                # Lógica JavaScript específica de cada página
│   │           ├── inicio.js
│   │           ├── login.js
│   │           ├── torneos.js
│   │           ├── partidos.js
│   │           ├── admin.js
│   │           └── ...
│   │
│   ├── pages/                        # Vistas secundarias de la aplicación
│   │   ├── login.html                # Inicio de sesión
│   │   ├── registro.html             # Registro de estudiantes
│   │   ├── recuperar.html            # Restablecimiento de contraseña
│   │   ├── panel.html                # Dashboard del usuario
│   │   ├── admin.html                # Panel de control de administración
│   │   ├── torneos.html              # Listado y detalle de torneos
│   │   ├── equipos.html              # Catálogo y detalle de equipos
│   │   ├── partidos.html             # Calendario de encuentros y actas
│   │   ├── tabla-posiciones.html     # Tabla de clasificación
│   │   ├── goles.html                # Tabla de máximos goleadores
│   │   ├── noticias.html             # Listado de noticias
│   │   ├── noticia.html              # Detalle de noticia con comentarios
│   │   ├── notificaciones.html       # Bandeja de notificaciones
│   │   ├── perfil.html               # Configuración de cuenta y perfil
│   │   └── nosotros.html             # Información institucional DMC
│   │
│   └── inicio.html                   # Página de bienvenida / Landing page
│
└── README.md                         # Documentación general del proyecto
```

---

## 📋 Requisitos Previos

Asegúrate de contar con lo siguiente instalado en tu sistema:

1. **Python 3.10 o superior** (asegúrate de marcar la casilla *"Add Python to PATH"* durante la instalación en Windows).
2. **XAMPP** (con los servicios de **Apache** y **MySQL** instalados).
3. **Navegador web moderno** (Google Chrome, Mozilla Firefox, Microsoft Edge o Brave).
4. *(Opcional)* **Visual Studio Code** con la extensión **Live Server**.

---

## 🚀 Guía de Instalación y Puesta en Marcha

### 1. Iniciar Base de Datos (XAMPP / MySQL)
1. Abre el panel de control de **XAMPP**.
2. Haz clic en el botón **Start** junto al módulo **MySQL** (y Apache si lo deseas).
3. Verifica que MySQL quede activo en el puerto `3306`.
> 💡 *Nota:* El backend creará automáticamente la base de datos `digital_sports_dmc` y sus tablas con codificación `utf8mb4` al iniciarse por primera vez si no existen.

---

### 2. Configurar el Entorno Virtual de Python
Abre una terminal (PowerShell, CMD o Bash) y colócate en la carpeta del backend:

```powershell
cd "Backend-Digital Sports"
```

Crea el entorno virtual:
```powershell
python -m venv venv
```
*(Si usas el launcher de Python en Windows, también puedes ejecutar `py -m venv venv`).*

Activa el entorno virtual:
- **Windows (PowerShell):**
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
  *(Si PowerShell bloquea la ejecución de scripts, ejecuta antes: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*
- **Windows (CMD):**
  ```cmd
  venv\Scripts\activate.bat
  ```
- **macOS / Linux:**
  ```bash
  source venv/bin/activate
  ```

---

### 3. Instalar Dependencias del Backend
Con el entorno virtual activo, instala las librerías necesarias:

```bash
pip install -r backend/requirements.txt
```

---

### 4. Configurar Variables de Entorno (`.env`)
En la carpeta `Backend-Digital Sports`, verifica o crea el archivo `.env` tomando como base `.env.example`:

```powershell
# En Windows PowerShell:
Copy-Item .env.example .env

# En Windows CMD:
copy .env.example .env
```

Contenido por defecto recomendado para desarrollo con XAMPP:
```ini
FLASK_CONFIG=development
SECRET_KEY=clave-secreta-para-desarrollo-dmc
DATABASE_URL=mysql+pymysql://root:@localhost:3306/digital_sports_dmc
ADMIN_NOMBRE=Administrador
ADMIN_CORREO=admin@digitalsports.com
ADMIN_PASSWORD=Admin12345
PERMITIR_MULTIPLES_EQUIPOS_POR_TORNEO=false
CORS_ORIGINS=http://localhost:5500,http://127.0.0.1:5500,http://localhost:5000,http://127.0.0.1:5000
GOOGLE_CLIENT_ID=53506546078-darvikfmuq16rl9n9u922qhsh0eeg4ms.apps.googleusercontent.com
FRONTEND_URL=http://localhost:5000
SESSION_COOKIE_SECURE=false
```

---

### 5. Inicializar la Base de Datos y Migraciones
Aplica las tablas y migraciones de esquema mediante el comando CLI de Flask:

```bash
flask --app run.py migrar
```

Si deseas crear manualmente un usuario administrador personalizado:
```bash
flask --app run.py crear-admin
```

---

### 6. Cargar Datos de Prueba (Opcional recomendado)
Para probar la plataforma con un escenario realista completo (torneos, equipos, docentes, estudiantes, partidos jugados, partidos programados, goles, amonestaciones y noticias), ejecuta:

```bash
flask --app run.py datos-prueba
```

> ⚠️ *Este comando solo se ejecuta si la base de datos no tiene torneos previos para evitar mezclar registros.*

---

### 7. Iniciar el Servidor Backend
Inicia la aplicación ejecutando `run.py`:

```bash
python run.py
```
*(o `py run.py`)*

Verás una salida similar en consola:
```text
============================================================
  DIGITAL SPORTS DMC — Backend (Flask + MySQL / XAMPP)
============================================================
  Aplicación: http://localhost:5000
  API REST:   http://localhost:5000/api
============================================================
```

---

### 8. Abrir la Aplicación (Frontend)

Tienes **dos opciones** compatibles para interactuar con la aplicación:

#### Opción A: Directamente a través de Flask (Recomendada)
El backend de Flask está configurado para servir automáticamente los archivos estáticos del frontend.  
Simplemente abre tu navegador y visita:
👉 **[http://localhost:5000](http://localhost:5000)** (o directamente **[http://localhost:5000/inicio.html](http://localhost:5000/inicio.html)**).

#### Opción B: Con VS Code Live Server
Si prefieres editar los archivos del frontend y disfrutar de recarga automática en vivo:
1. Abre la carpeta `Frontend-Digital Sports` en Visual Studio Code.
2. Haz clic derecho sobre `inicio.html` y selecciona **Open with Live Server** (normalmente abre en `http://localhost:5500`).
3. El archivo `assets/js/core/api.js` detectará automáticamente que estás en Live Server y redirigirá todas las peticiones hacia la API en `http://localhost:5000/api`.

---

## 👥 Cuentas de Acceso y Roles de Prueba

Si ejecutaste el comando `flask --app run.py datos-prueba`, tienes a tu disposición las siguientes credenciales de prueba preconfiguradas:

| Rol | Correo Electrónico | Contraseña | Permisos y Capacidades |
| :--- | :--- | :--- | :--- |
| **Administrador** | `admin@dmc.edu.co` | `Admin12345` | Control total del sistema: gestión de usuarios, torneos, aprobación de noticias, actas de partidos y registro de auditoría. |
| **Docente** | `carlos.rodriguez@dmc.edu.co` | `Docente123` | Crear y gestionar equipos a su cargo, inscribir estudiantes en plantillas y registrar dorsales. |
| **Docente** | `julio.herrera@dmc.edu.co` | `Docente123` | Gestión de equipos asignados (ej. cursos noveno, décimo, interroscas). |
| **Docente** | `viviana.martinez@dmc.edu.co` | `Docente123` | Gestión de equipos femeninos y torneos interclases. |
| **Estudiante** | *(Cuentas generadas en el seeder)* | `Estudiante123` | Consultar estado de su equipo, próximos partidos, tabla de goleadores y redactar comentarios en noticias. |
| **Visitante** | *(Sin iniciar sesión)* | N/A | Acceso de solo lectura a torneos vigentes, tablas de posiciones, partidos, goles e información institucional. |

---

## 🔑 Configuración de la API de Google (Google Sign-In / OAuth 2.0)

La plataforma integra **Google Identity Services** para permitir que estudiantes y usuarios se registren o inicien sesión con un solo clic utilizando sus cuentas de Google (personales o del dominio educativo `@dmc.edu.co`).

### ⚙️ 1. Dónde se configura
La integración se controla desde la variable de entorno `GOOGLE_CLIENT_ID` en el archivo `Backend-Digital Sports/.env`:

```ini
GOOGLE_CLIENT_ID=53506546078-darvikfmuq16rl9n9u922qhsh0eeg4ms.apps.googleusercontent.com
```

### 🔄 2. Cómo funciona el flujo
1. **Detección dinámica:** Al ingresar a `pages/login.html` o `pages/registro.html`, el frontend realiza una petición a `GET /api/usuarios/auth-config`.
2. **Renderizado del botón oficial:** Si el backend tiene un `GOOGLE_CLIENT_ID` configurado, la librería de Google (`https://accounts.google.com/gsi/client`) renderiza automáticamente el botón *"Continuar con Google"*. Si no está configurado, el sistema oculta el botón o muestra un aviso informativo sin romper el login tradicional con usuario y contraseña.
3. **Generación del Token:** El usuario selecciona su cuenta de Google y Google emite un token JWT firmado (`credential`).
4. **Verificación y alta de usuario:** El frontend envía el token al endpoint `POST /api/usuarios/google-login`. El backend verifica la autenticidad del token con la librería oficial `google-auth` (`id_token.verify_oauth2_token`), extrae el correo, nombre y foto de perfil, y:
   - Si el usuario ya existe, inicia sesión de inmediato mediante la cookie segura de sesión `dsdmc_sesion`.
   - Si no existe, crea automáticamente la cuenta con rol `estudiante` y abre la sesión.

### 🌐 3. Pasos para obtener o cambiar tu propio Google Client ID (Google Cloud Console)
Si deseas generar tus propias credenciales en Google:
1. Ingresa a [Google Cloud Console](https://console.cloud.google.com/).
2. Crea un proyecto nuevo (ej. `Digital Sports DMC`).
3. Ve a **APIs y servicios** > **Pantalla de consentimiento de OAuth**:
   - Selecciona **Externo** (o **Interno** si tienes Google Workspace institucional) y presiona *Crear*.
   - Ingresa el nombre de la app (ej. *Digital Sports DMC*) y los correos de contacto. Guarda los cambios.
4. Ve a **APIs y servicios** > **Credenciales**:
   - Haz clic en **+ Crear credenciales** > **ID de cliente de OAuth**.
   - Tipo de aplicación: selecciona **Aplicación web**.
   - En **Orígenes autorizados de JavaScript**, añade:
     - `http://localhost:5000` *(para cuando Flask sirve el frontend)*
     - `http://localhost:5500` *(para cuando usas Live Server en VS Code)*
     - `http://127.0.0.1:5000`
     - `http://127.0.0.1:5500`
   - Haz clic en **Crear**.
5. Copia el **ID de cliente** generado y pégalo en el archivo `Backend-Digital Sports/.env` en la variable `GOOGLE_CLIENT_ID`.
6. Reinicia el servidor Flask (`python run.py`).

---

## 🏛 Arquitectura del Sistema

El sistema implementa una arquitectura modular desacoplada:

1. **Patrón MVC en Backend:**
   - **Modelos (`models/`):** Clases ORM con SQLAlchemy que mapean las entidades de base de datos con relaciones `One-to-Many` y `Many-to-Many` (p. ej. `Equipo` ↔ `Estudiante` mediante la tabla intermedia `equipo_estudiante`).
   - **Controladores (`controllers/`):** Encargados de la validación de peticiones, control de permisos por rol, lógica de transacción y armado de respuestas estandarizadas.
   - **Rutas (`routes/`):** Blueprints modulares que exponen endpoints HTTP limpios.
   - **Servicios (`services/`):** Algoritmos de negocio independientes como el cálculo de posiciones y estadísticas deportivas.
2. **Seguridad Integral:**
   - **Sesión del lado del servidor:** Las credenciales nunca se guardan en `localStorage`. Se utiliza una cookie de sesión cifrada `dsdmc_sesion` protegida con `HttpOnly`.
   - **Defensa CSRF:** Cada petición mutante (`POST`, `PUT`, `DELETE`) valida la presencia de la cabecera `X-Requested-With` / `X-CSRFToken`.
   - **Hashes Criptográficos:** Contraseñas protegidas mediante algoritmos de hash seguros provistos por `werkzeug.security`.
3. **Frontend Reactivo y Sin Dependencias Pesadas:**
   - El cliente `api.js` maneja automáticamente los estados de carga con spinners, toasts de notificación interactivos y captura de errores estructurados de la API.
   - El módulo `layout.js` renderiza dinámicamente el Navbar y Sidebar ajustando las opciones de navegación según los privilegios del usuario autenticado.

---

## 📡 Referencia de la API REST

Todos los endpoints se encuentran prefijados por `/api`:

### 🔐 Autenticación y Usuarios (`/api/usuarios`)
- `GET /api/usuarios/auth-config` — Obtener la configuración pública de autenticación (retorna `google_client_id`).
- `POST /api/usuarios/login` — Iniciar sesión con correo y contraseña.
- `POST /api/usuarios/registro` — Registro de nuevo estudiante.
- `POST /api/usuarios/google-login` — Autenticación y registro federado con Google OAuth 2.0.
- `POST /api/usuarios/logout` — Cerrar sesión activa.
- `GET /api/usuarios/sesion` — Obtener información del usuario autenticado actual.
- `POST /api/usuarios/recuperar` — Solicitar enlace de recuperación de contraseña.
- `POST /api/usuarios/restablecer` — Aplicar nueva contraseña mediante token.
- `GET /api/usuarios/perfil` / `PUT /api/usuarios/perfil` — Consultar y actualizar perfil propio.
- `GET /api/usuarios` / `POST /api/usuarios` — Gestión de usuarios (Solo Admin).

### 🏆 Torneos (`/api/torneos`)
- `GET /api/torneos` — Listar todos los torneos disponibles.
- `POST /api/torneos` — Crear un nuevo torneo (Admin).
- `GET /api/torneos/<id>` — Detalle del torneo y configuración.
- `PUT /api/torneos/<id>` / `DELETE /api/torneos/<id>` — Modificar o archivar torneo (Admin).

### ⚽ Equipos y Plantillas (`/api/equipos`)
- `GET /api/equipos` — Listar equipos (filtrable por torneo o docente).
- `POST /api/equipos` — Inscribir un nuevo equipo (Docente / Admin).
- `GET /api/equipos/<id>` — Ficha técnica del equipo e integrantes.
- `POST /api/equipos/<id>/integrantes` — Añadir estudiante a la plantilla del equipo.
- `DELETE /api/equipos/<id>/integrantes/<id_estudiante>` — Retirar estudiante del equipo.

### 📅 Partidos y Actas (`/api/partidos`)
- `GET /api/partidos` — Calendario de encuentros (filtros por fecha, estado y torneo).
- `POST /api/partidos` — Programar nuevo encuentro (Admin).
- `GET /api/partidos/<id>` — Detalle del partido, alineaciones y eventos.
- `PUT /api/partidos/<id>` — Actualizar marcador, estado o lugar.
- `POST /api/partidos/<id>/finalizar` — Cerrar acta y actualizar tabla de posiciones.

### 🎯 Goles y Faltas (`/api/goles`, `/api/faltas`)
- `POST /api/goles` — Registrar anotación en un partido.
- `GET /api/goles/tabla` — Obtener tabla de goleadores por torneo.
- `POST /api/faltas` — Registrar tarjeta amarilla o roja con motivo.

### 📊 Clasificación (`/api/posiciones`)
- `GET /api/posiciones/<id_torneo>` — Obtener tabla de clasificación oficial actualizada.

### 📰 Noticias y Comentarios (`/api/noticias`)
- `GET /api/noticias` — Listado de noticias publicadas.
- `POST /api/noticias` — Publicar nueva nota informativa (Admin).
- `GET /api/noticias/<id>/comentarios` — Listar comentarios de una noticia.
- `POST /api/noticias/<id>/comentarios` — Agregar comentario (Usuarios autenticados).

### 🔔 Notificaciones y Auditoría
- `GET /api/notificaciones` — Listar notificaciones del usuario actual.
- `PUT /api/notificaciones/<id>/leida` — Marcar notificación como leída.
- `GET /api/auditoria` — Registro de auditoría del sistema (Solo Admin).
- `POST /api/subir-imagen` — Carga de escudos o imágenes de noticias (PNG, JPG, WEBP).
- `GET /api/salud` — Comprobación de disponibilidad del servicio (`health check`).

---

## 🧪 Pruebas Automatizadas (Testing)

El proyecto incluye pruebas automatizadas con **Pytest** que validan la autenticación, flujos de torneos, fixture de partidos, clasificación matemática y seguridad contra inyecciones y accesos no autorizados.

Para correr la suite de pruebas:
1. Activa el entorno virtual en `Backend-Digital Sports`.
2. Ejecuta:
   ```bash
   pytest
   ```
   O con reporte detallado:
   ```bash
   pytest -v
   ```

> 💡 *Las pruebas utilizan una base de datos SQLite en memoria aislada (`sqlite://`), por lo que pueden ejecutarse sin interferir con tu base de datos MySQL local de XAMPP.*

---

## ❓ Solución de Problemas Frecuentes (FAQ)

### 1. `OperationalError: (2003, "Can't connect to MySQL server on 'localhost:3306'")`
- **Causa:** El servicio de MySQL no está iniciado o está bloqueado.
- **Solución:** Abre el panel de control de **XAMPP** y asegúrate de presionar el botón **Start** en el servicio **MySQL**. Si tienes otro servicio en el puerto 3306 (como MySQL Server instalado por separado), detén dicho servicio o ajusta el puerto en el archivo `.env`.

### 2. `'python' o 'pip' no se reconoce como un comando interno o externo`
- **Causa:** Python no se agregó al `PATH` del sistema de Windows.
- **Solución:** Puedes invocar a Python usando el launcher oficial de Windows ejecutando `py -m venv venv` y `py run.py`. Alternativamente, reinstala Python marcando la opción *"Add Python to PATH"*.

### 3. Error de CORS al usar Live Server
- **Causa:** El puerto de tu Live Server no coincide con los autorizados en el backend.
- **Solución:** Revisa tu archivo `.env` en `Backend-Digital Sports/.env` y asegúrate de que `CORS_ORIGINS` incluya la URL de tu Live Server (por ejemplo `http://localhost:5500` o `http://127.0.0.1:5500`).

### 4. `Puerto 5000 ya está en uso`
- **Causa:** Hay otra instancia del servidor o un proceso ocupando el puerto 5000.
- **Solución:** En Windows PowerShell puedes verificar qué proceso usa el puerto con `Get-Process -Id (Get-NetTCPConnection -LocalPort 5000).OwningProcess` y cerrarlo, o definir en tu archivo `.env`:
  ```ini
  PORT=5001
  ```

---

## 📄 Licencia y Reconocimientos

Desarrollado para el proyecto formativo de la **IED Diego Montaña Cuéllar — DMC (Ficha 3215869)**.  
Uso académico y formativo.
