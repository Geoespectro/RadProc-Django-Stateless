import os
from procesamiento import service

def test_procesamiento_agua_minimal():
    ruta_json = os.path.join("procesamiento", "tests", "fixtures", "agua_tests.json")
    resultado = service.run_processing_from_json_file("agua", ruta_json)

    assert resultado is not None
    assert "produced" in resultado
    assert isinstance(resultado["produced"], list)

