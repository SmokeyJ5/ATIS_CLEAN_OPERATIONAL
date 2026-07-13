import importlib


def test_stable_certification_entrypoint():
    module = importlib.import_module("tests.stable_certification")
    module.main()


def test_v4_architecture_smoke_entrypoint():
    module = importlib.import_module("tests.v4_architecture_smoke")
    module.main()
