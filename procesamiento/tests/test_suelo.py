import os
from procesamiento import service

def test_procesamiento_suelo_minimal():
    ruta_json = os.path.join("procesamiento", "tests", "fixtures", "suelo_tests.json")
    resultado = service.run_processing_from_json_file("suelo", ruta_json)

    assert resultado is not None
    assert "produced" in resultado
    assert isinstance(resultado["produced"], list)


