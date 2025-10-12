# procesamiento/tests/conftest.py (archivo nuevo)
import shutil
import os
import pytest

@pytest.fixture(autouse=True)
def cleanup_tmp_dirs():
    yield
    shutil.rmtree("/tmp/input", ignore_errors=True)
    shutil.rmtree("/tmp/output", ignore_errors=True)
