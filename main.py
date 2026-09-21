"""Application entry point for the standalone ML inference service."""

from maxsmartcity.ml.service import create_app

app = create_app()


def main() -> None:
    print("Run the ML service with: uv run litestar --app main:app run")


if __name__ == "__main__":
    main()
