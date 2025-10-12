#!/bin/bash
set -e

echo "==> Iniciando contenedor del Core de RadProc..."
python -m procesamiento.service
