# 🖥️ Interfaz Web – RadProc (Frontend Django)

Este módulo contiene la **interfaz web del sistema RadProc**, desarrollada con **Django**, **HTML/CSS/JavaScript** y **Bootstrap**, que permite a los usuarios cargar conjuntos de datos espectrales, configurar parámetros de procesamiento y obtener resultados generados por el **núcleo (RadProc Core)** de forma gráfica y controlada.

Opera en conjunto con el contenedor del core (`radproc-core`), comunicándose mediante llamadas internas (sin estado).

---

## 🧠 Descripción general

La interfaz RadProc fue diseñada para:

* Proporcionar una experiencia de usuario intuitiva para el procesamiento espectral.
* Validar y enviar los datos al núcleo del sistema (procesamiento stateless).
* Permitir la configuración avanzada de parámetros y referencias (`Spectralon`, `spectrum`, `meas_order`, `target_list`).
* Visualizar mensajes, logs y resultados mediante un sistema de modales y registros en tiempo real.
* Mantener separación total entre la capa de presentación (frontend) y la capa de cálculo (backend).

---

## 📂 Estructura del módulo

```bash
interfaz/
├── admin.py                 ← Registro Django admin (mínimo)
├── apps.py                  ← Configuración de la app Django
├── models.py                ← Modelos básicos (si se usan configuraciones persistentes)
├── urls.py                  ← Definición de rutas locales
├── views.py                 ← Controladores principales de la interfaz
│
├── services/                ← Servicios auxiliares
│   └── processing.py        ← Puente con el núcleo (procesamiento/service.py)
│
├── static/                  ← Recursos estáticos (CSS, JS, imágenes, sonidos)
│   ├── css/
│   │   ├── base.css         ← Estilos generales
│   │   ├── config.css       ← Estilos para panel de configuración
│   │   └── index.css        ← Estilos para la página principal
│   ├── js/
│   │   ├── index.js         ← Lógica principal de carga, validación y envío
│   │   ├── config.js        ← Gestión dinámica de configuraciones
│   │   ├── validacionResultado.js ← Modal de validación (errores 422)
│   │   ├── main.js          ← Comportamientos globales (botones, feedback)
│   │   ├── sound.js         ← Control de sonidos al finalizar procesos
│   │   └── …                ← Archivos auxiliares
│   ├── img/
│   │   ├── logo_conae.png
│   │   ├── radproc.ico
│   │   └── radproc_logo.svg
│   └── sounds/
│       └── fin.mp3          ← Sonido de finalización
│
├── templates/               ← Plantillas HTML de Django
│   ├── main/
│   │   ├── base.html        ← Plantilla base (layout general)
│   │   ├── index.html       ← Página principal de carga
│   │   ├── configuraciones.html ← Panel de configuración avanzada
│   │   └── editar_spectralon.html ← Editor de archivo de referencia
│   └── docs/
│       └── guia_usuario.html ← Documentación embebida (manual)
│
├── static/docs/guia_usuario.css ← Estilos para el manual de usuario
└── tests.py                 ← Pruebas básicas de vistas y rutas
```

---

## ⚙️ Flujo de procesamiento (interfaz → núcleo)

1. **El usuario** selecciona un tipo de medición (agua o suelo).
2. Carga un archivo `.zip` con los datos espectrales.
3. Define parámetros (`spectrum`, `meas_order`, `target_list`, `Spectralon`, etc.).
4. Al presionar “Procesar”, la vista principal envía los datos mediante `views.py` → `services/processing.py`.
5. `processing.py` empaqueta los datos, los valida y llama internamente al **núcleo (`process_zip`)**.
6. El núcleo ejecuta el procesamiento y devuelve un nuevo ZIP con los resultados.
7. La interfaz muestra mensajes en tiempo real en el área de logs (`textarea`) y lanza un **modal informativo** en caso de configuraciones inválidas (422).

---

## 🧩 Lógica interna

### `views.py`

Controla las rutas y acciones principales:

* `/` → Página principal (carga de datos).
* `/configuraciones/` → Panel de configuración.
* `/guardar_config/` → Actualiza parámetros en sesión.
* `/procesar/` → Envía datos al core.
* `/limpiar_sesion/` → Restablece estado.

### `services/processing.py`

Actúa como **interfaz de comunicación** con el núcleo de procesamiento (`procesamiento/service.py`):

* Lee los datos del formulario.
* Aplica validaciones previas.
* Maneja las excepciones controladas (`ConfigValidationError` → HTTP 422).
* Devuelve al usuario el archivo ZIP resultante o el mensaje de error formateado.

### `static/js/validacionResultado.js`

Maneja el modal que se activa cuando el core devuelve un error de validación:

* Muestra mensajes explicativos (error 422).
* Ofrece guía visual de corrección para el usuario.
* Permite acceder a detalles técnicos de configuración.

---

## 🚀 Ejecución local (modo desarrollo)

Desde la raíz del proyecto:

```bash
source venv/bin/activate
python manage.py runserver
```

📍 La aplicación quedará disponible en:
[http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 🐳 Ejecución en modo contenedor (Docker)

### 🔧 1. Construcción de imagen

```bash
docker build -t radproc-web -f docker/interfaz/Dockerfile .
```

### ▶️ 2. Ejecución del contenedor

```bash
docker run -it --rm -p 8000:8000 radproc-web
```

📍 Interfaz disponible en:
[http://localhost:8000](http://localhost:8000)

---

## 🧪 Pruebas unitarias

El módulo incluye **tests básicos de salud (health checks)** que validan el funcionamiento de las rutas principales de la interfaz en modo *stateless*.

### ▶️ Ejecución

Desde la raíz del proyecto:

```bash
source venv/bin/activate
pytest interfaz/tests.py -v
```

📍 Asegurate de tener `pytest-django` instalado y el archivo `pytest.ini` configurado con:

```ini
[pytest]
DJANGO_SETTINGS_MODULE = web.settings
```

---

### ✅ Resultado esperado

```
collected 2 items
interfaz/tests.py::test_configuraciones_view_status PASSED
interfaz/tests.py::test_index_view_status PASSED
=========================== 2 passed in 0.4s ============================
```

---

### 🧩 Descripción

* **`test_index_view_status`** → Verifica que la página principal (`/`) responda correctamente.
* **`test_configuraciones_view_status`** → Comprueba que el panel de configuraciones (`/configuraciones/`) esté disponible.

---

## 🧱 Dependencias principales

Ver archivo: `docker/interfaz/requirements.txt`

Incluye:

```text
django
requests
python-multipart
gunicorn
```

*(más las dependencias del core para desarrollo local compartido)*

---

## 🔄 Integración futura (GitHub Actions)

👉 Pendiente de agregar.
El flujo planificado incluirá:

* Construcción automática del contenedor `radproc-web`.
* Ejecución de pruebas unitarias en entorno Django.
* Publicación de la imagen en el registro interno.

---

## 🏷️ Créditos

Desarrollado por **Juan Carlos Quinteros.**
Proyecto **RadProc – Comisión Nacional de Actividades Espaciales (CONAE)**
Uso interno bajo licencia institucional.

---


