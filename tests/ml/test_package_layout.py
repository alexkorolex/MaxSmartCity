from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_ml_runtime_is_a_top_level_src_layer() -> None:
    assert (ROOT / "src" / "ml" / "service" / "app.py").is_file()
    assert not (ROOT / "maxsmartcity" / "__init__.py").exists()


def test_backend_ml_gateway_does_not_import_runtime_implementation() -> None:
    gateway_sources = (ROOT / "src" / "domains" / "ml").glob("*.py")

    for source in gateway_sources:
        content = source.read_text(encoding="utf-8")
        assert "from src.ml" not in content
        assert "import src.ml" not in content


def test_ml_docker_image_uses_the_new_package_path() -> None:
    dockerfile = (ROOT / "Dockerfile.ml").read_text(encoding="utf-8")

    assert "COPY src/ml ./src/ml" in dockerfile
    assert "maxsmartcity.ml" not in dockerfile
    assert "COPY maxsmartcity" not in dockerfile
