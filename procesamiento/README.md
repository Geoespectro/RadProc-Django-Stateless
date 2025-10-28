# ⚙️ Núcleo de Procesamiento – RadProc Core (Stateless)

Este módulo contiene el **núcleo de procesamiento espectral** del sistema **RadProc**, encargado de interpretar, calibrar y procesar mediciones espectrales de **suelo** y **agua**.  
Opera en modo **stateless**, mediante una **API REST (FastAPI)**, apta para integrarse con la interfaz web o utilizarse de forma independiente.

---

## 🧠 Descripción general

El Core de RadProc fue diseñado para:
- Ejecutarse dentro de un contenedor Docker autónomo.
- Procesar archivos ZIP con mediciones espectrales.
- Generar resultados autocontenidos (`.txt`, `.png`, `.json`) dentro de un ZIP de salida.
- Mantener independencia total de la interfaz gráfica.

---

## 📂 Estructura del módulo

```bash
procesamiento/
├── app.py                   ← Servidor FastAPI (punto de entrada del contenedor)
├── service.py               ← Orquestador principal del procesamiento
├── base.py                  ← Contrato base para todos los procesadores
├── validators/              ← Validadores de configuración
│   └── config_validator.py  ← Valida coherencia entre datos y parámetros
├── processors/              ← Procesadores especializados
│   ├── agua.py
│   └── suelo.py
├── aux/                     ← Funciones auxiliares (cálculos, lectura, gráficos)
│   ├── aux_func.py
│   └── aux_func_w.py
├── configs/                 ← Configuraciones base y calibraciones
│   ├── agua.json
│   ├── suelo.json
│   └── Spectralon/SRT-99-120.txt
└── tests/                   ← Pruebas unitarias
```

---

## 🚀 Ejecución en modo API (Docker)

### 🔧 1. Construcción del contenedor

```bash
# Desde la raíz del proyecto
docker build -t radproc-core -f docker/core/Dockerfile .
```

### ▶️ 2. Ejecución del contenedor

```bash
docker run -it --rm -p 8080:8080 radproc-core
```

📍 El servicio quedará disponible en
[http://localhost:8080/docs](http://localhost:8080/docs)

---

## 🌐 Endpoints principales (FastAPI)

| Método | Ruta    | Descripción                                                             |
| ------ | ------- | ----------------------------------------------------------------------- |
| `POST` | `/run`  | Recibe un archivo `.zip` con mediciones y devuelve un `.zip` procesado. |
| `GET`  | `/docs` | Interfaz Swagger para pruebas y documentación interactiva.              |

### Ejemplo rápido con `curl`

```bash
curl -s -X POST \
  -F "zip=@/ruta/a/tus_datos/208-20230516-CHAJARI.zip" \
  http://localhost:8080/run \
  -o salida.zip
```

---

## 🧩 Lógica interna

### `app.py`

Contiene la aplicación **FastAPI** y define el endpoint `/run`.
Llama internamente a las funciones del módulo `service.py`.

### `service.py`

Coordina el flujo de procesamiento:

1. Descomprime el archivo ZIP.
2. Detecta tipo de medición (`agua` o `suelo`).
3. Ejecuta el procesador correspondiente.
4. Genera los resultados y los empaqueta nuevamente en un `.zip`.

### `validators/config_validator.py`

Verifica la coherencia entre el conjunto de datos cargado y la configuración seleccionada.
Si detecta inconsistencias, bloquea la ejecución y devuelve un error controlado (HTTP 422) con detalles técnicos.

---

## 📦 Dependencias principales

Ver archivo: `docker/core/requirements.txt`

Incluye:

```text
fastapi
uvicorn
python-multipart
numpy
matplotlib
imageio
watchdog
boto3
s3fs
netCDF4
cartopy
```

---

## 🧪 Pruebas unitarias

Ejecutar desde la raíz del proyecto:

```bash
source venv/bin/activate
pytest procesamiento/tests -v
```

---

## 🔄 Integración continua (GitHub Actions)

Este módulo cuenta con un **workflow activo en GitHub Actions** que:
- Construye automáticamente la imagen Docker del core (`radproc-core`).
- Ejecuta las pruebas unitarias dentro del contenedor.
- Informa el resultado del build en la pestaña **Actions** del repositorio.

📦 El workflow se activa automáticamente con cada *push* o *pull request* a la rama principal  
y publica la imagen con el tag `radproc-core:latest`.


---

## 🏷️ Créditos

Desarrollado por **Juan Carlos Quinteros.**
Proyecto **RadProc – Comisión Nacional de Actividades Espaciales (CONAE)**
Uso interno bajo licencia institucional.

---






