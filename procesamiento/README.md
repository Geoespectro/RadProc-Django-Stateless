# 🧠 Núcleo de Procesamiento – RadProc

Este módulo contiene el **core de procesamiento espectral** del proyecto **RadProc**, responsable de interpretar archivos de medición (suelo y agua), aplicar calibraciones, generar gráficas y devolver resultados listos para análisis.

---

## 📘 Descripción general

El núcleo de RadProc está diseñado como una **unidad desacoplada y stateless**, apta para integrarse con interfaces web, APIs o ejecutarse de forma autónoma.
Opera sobre directorios de entrada o configuraciones JSON, y produce salidas autocontenidas con metadatos completos.

---

## ⚙️ Funcionalidades principales

* Procesamiento espectral para **agua** y **suelo/planta**
* Identificación automática de bloques `spectralon` y `target`
* Cálculo de **reflectancia calibrada**
* Exportación de:

  * Archivos `.txt` procesados
  * Gráficos `.png`
  * Metadatos en `.json`
* Modularidad total y soporte para pruebas unitarias (`pytest`)
* Integración lista para contenedores Docker y CI/CD

---

## 📂 Estructura del módulo

```bash
procesamiento/
├── service.py               ← Orquestador general del procesamiento
├── base.py                  ← Protocolo común para los procesadores
├── processors/              ← Lógica específica de cada tipo
│   ├── agua.py
│   └── suelo.py
├── aux/                     ← Funciones auxiliares y cálculos
│   ├── aux_func.py
│   └── aux_func_w.py
├── configs/                 ← Configuraciones y archivos patrón
│   ├── agua.json
│   ├── suelo.json
│   └── Spectralon/SRT-99-120.txt
└── tests/                   ← Pruebas unitarias y fixtures
```

---

## 🧩 Componentes principales

### `service.py`

Orquesta el flujo completo de procesamiento.
Funciones clave:

* `process_zip()` – Ejecuta procesamiento a partir de un ZIP comprimido.
* `process_folder_to_zip()` – Procesa una carpeta y genera un ZIP con resultados.
* `run_processing_from_json_file()` – Permite ejecutar pruebas con configuraciones JSON.

---

### `processors/agua.py` y `processors/suelo.py`

Procesadores especializados.
Realizan:

* Lectura de espectros crudos
* Agrupación por tipo (`target` / `spectralon`)
* Cálculos físicos (reflectancia)
* Exportación de resultados y gráficos

---

### `aux/aux_func.py` y `aux_func_w.py`

Funciones de utilidad:

* Lectura tolerante de archivos `.txt` generados por ViewSpec Pro
* Cálculo de índices espectrales
* Cálculo de errores de reflectancia
* Generación de gráficos `matplotlib` sin entorno gráfico (modo “Agg”)

---

### `configs/`

Contiene parámetros por defecto de ejecución:

* `agua.json` y `suelo.json` con configuraciones base.
* Carpeta `Spectralon/` con archivo patrón `SRT-99-120.txt`.

---

## 🧪 Pruebas unitarias

El módulo incluye un conjunto de pruebas automáticas con `pytest`.

### Estructura de pruebas

```bash
procesamiento/tests/
├── test_agua.py
├── test_suelo.py
├── test_errores.py
└── fixtures/
    ├── agua_tests.json
    ├── suelo_tests.json
    └── data/
        ├── agua/agua_test_spectra.txt
        └── suelo/suelo_test_spectra.txt
```

### Ejecución de pruebas

```bash
source venv/bin/activate
PYTHONPATH=. pytest procesamiento/tests/ -v
```

---

## 🧱 Integración con Docker

El núcleo cuenta con su propio contenedor definido en `docker/core/`.
Se puede construir y ejecutar de forma independiente:

```bash
# Construir la imagen
docker build -f docker/core/Dockerfile -t radproc-core .

# Ejecutar el contenedor
docker run --rm -it radproc-core
```

El contenedor ejecuta automáticamente `procesamiento.service` en modo stateless.

---

## 🔄 Integración continua (CI/CD)

Este módulo está preparado para pipelines automáticos (GitHub Actions o Gitea).
Al incluir un archivo `build_core.yml`, el contenedor se construye y valida de forma continua al realizar commits o merges en ramas activas.

---

## 🔐 Requisitos

* **Python 3.10+**
* Dependencias: ver `docker/core/requirements.txt`
* Estructura de archivos espectrales compatible con **ViewSpec Pro**

---

## 🏷️ Licencia y créditos

Desarrollado por **CONAE (Comisión Nacional de Actividades Espaciales)**
Proyecto RadProc – Núcleo de Procesamiento Espectral
Uso interno bajo licencia institucional.

---




