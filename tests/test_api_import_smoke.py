import importlib


def test_api_module_imports():
    module = importlib.import_module("api.main")
    assert getattr(module, "app", None) is not None
