# MaxSmartCity

Для разработки нужны Python 3.12+ и [uv](https://docs.astral.sh/uv/).

После клонирования установите зависимости и Git-хук:

```bash
uv sync --locked --group dev
uv run --locked pre-commit install
```

[pre-commit](https://pre-commit.com/) перед каждым коммитом запускает проверки
всего проекта: `ruff check .`, `ruff format --check .`, `ty check` и `pytest`.
Ошибка любой проверки блокирует коммит. Версии инструментов берутся из `uv.lock`;
хуки не исправляют код автоматически.

Запуск всех проверок вручную:

```bash
uv run --locked pre-commit run --all-files
```

Запуск только тестов:

```bash
uv run --locked pytest
```

Исправление замечаний Ruff и форматирование:

```bash
uv run --locked ruff check --fix .
uv run --locked ruff format .
```
