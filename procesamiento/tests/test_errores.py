import os
import pytest
from procesamiento import service

def test_config_invalida_lanza_error():
    ruta = os.path.join("procesamiento", "tests", "fixtures", "config_invalida.json")
    with pytest.raises(Exception):
        service.run_processing_from_json_file("agua", ruta)
