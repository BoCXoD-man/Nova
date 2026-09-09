"""
Модуль: commands/schema.py

Содержит правила и функции валидации структурированных ответов Butler.
Проверяет команды, параметры, результат, инструкцию Responder и решение
по долговременной памяти пользователя или связанных людей.
"""

from typing import Any


ALLOWED_COMMANDS = {
    "conversation",
    "weather",
    "music",
}

ALLOWED_MEMORY_ACTIONS = {
    "remember",
    "forget",
    "ignore",
}

ALLOWED_MEMORY_SUBJECT_TYPES = {
    "user",
    "person",
}


def validate_butler_response(data: Any) -> dict:
    """Проверяет структуру ответа Butler и возвращает валидные данные."""
    if not isinstance(data, dict):
        raise ValueError(
            "Butler должен вернуть JSON-объект."
        )

    required_fields = {
        "command",
        "parameters",
        "memory",
        "result",
        "prompt",
    }

    missing_fields = required_fields - data.keys()

    if missing_fields:
        raise ValueError(
            f"Butler не вернул обязательные поля: "
            f"{', '.join(missing_fields)}"
        )

    command = data["command"]

    if command not in ALLOWED_COMMANDS:
        raise ValueError(
            f"Неизвестная команда Butler: {command}"
        )

    if not isinstance(data["parameters"], dict):
        raise ValueError(
            "Поле 'parameters' должно быть объектом."
        )

    if data["result"] is not None and not isinstance(
        data["result"],
        str,
    ):
        raise ValueError(
            "Поле 'result' должно быть строкой или null."
        )

    if not isinstance(data["prompt"], str):
        raise ValueError(
            "Поле 'prompt' должно быть строкой."
        )

    _validate_command_parameters(
        command,
        data["parameters"],
    )

    _validate_memory(
        data["memory"]
    )

    return data


def _validate_command_parameters(
    command: str,
    parameters: dict,
) -> None:
    """Проверяет обязательные параметры выбранной команды Butler."""
    if command == "conversation":
        if "text" not in parameters:
            raise ValueError(
                "Для conversation требуется parameters.text."
            )

        if not isinstance(parameters["text"], str):
            raise ValueError(
                "parameters.text должен быть строкой."
            )

    elif command == "weather":
        if "city" not in parameters:
            raise ValueError(
                "Для weather требуется parameters.city."
            )

        if not isinstance(parameters["city"], str):
            raise ValueError(
                "parameters.city должен быть строкой."
            )

    elif command == "music":
        if "query" not in parameters:
            raise ValueError(
                "Для music требуется parameters.query."
            )

        if not isinstance(parameters["query"], str):
            raise ValueError(
                "parameters.query должен быть строкой."
            )


def _validate_memory(memory: Any) -> None:
    """Проверяет структуру и допустимые значения решения Butler по памяти."""
    if not isinstance(memory, dict):
        raise ValueError(
            "Поле 'memory' должно быть объектом."
        )

    required_fields = {
        "action",
        "subject_type",
        "subject_name",
        "subject_relation",
        "category",
        "key",
        "value",
        "confidence",
    }

    missing_fields = required_fields - memory.keys()

    if missing_fields:
        raise ValueError(
            f"В memory отсутствуют обязательные поля: "
            f"{', '.join(missing_fields)}"
        )

    action = memory["action"]
    subject_type = memory["subject_type"]
    subject_name = memory["subject_name"]
    subject_relation = memory["subject_relation"]
    category = memory["category"]
    key = memory["key"]
    value = memory["value"]
    confidence = memory["confidence"]

    if action not in ALLOWED_MEMORY_ACTIONS:
        raise ValueError(
            f"Неизвестное действие памяти: {action}"
        )

    if subject_type not in ALLOWED_MEMORY_SUBJECT_TYPES:
        raise ValueError(
            "memory.subject_type должен быть "
            "'user' или 'person'."
        )

    if subject_name is not None and not isinstance(
        subject_name,
        str,
    ):
        raise ValueError(
            "memory.subject_name должен быть строкой или null."
        )

    if subject_relation is not None and not isinstance(
        subject_relation,
        str,
    ):
        raise ValueError(
            "memory.subject_relation должен быть строкой или null."
        )

    if category is not None and not isinstance(
        category,
        str,
    ):
        raise ValueError(
            "memory.category должен быть строкой или null."
        )

    if key is not None and not isinstance(
        key,
        str,
    ):
        raise ValueError(
            "memory.key должен быть строкой или null."
        )

    if value is not None and not isinstance(
        value,
        str,
    ):
        raise ValueError(
            "memory.value должен быть строкой или null."
        )

    if not isinstance(confidence, (int, float)):
        raise ValueError(
            "memory.confidence должен быть числом."
        )

    if not 0.0 <= confidence <= 1.0:
        raise ValueError(
            "memory.confidence должен находиться "
            "в диапазоне от 0.0 до 1.0."
        )

    if action == "ignore":
        return

    if category is None:
        raise ValueError(
            f"Для memory.action='{action}' "
            f"требуется category."
        )

    if key is None:
        raise ValueError(
            f"Для memory.action='{action}' "
            f"требуется key."
        )

    if action == "remember" and value is None:
        raise ValueError(
            "Для memory.action='remember' "
            "требуется value."
        )

    if action in {
        "remember",
        "forget",
    } and subject_type == "person":
        if subject_name is None and subject_relation is None:
            raise ValueError(
                "Для памяти связанного человека требуется "
                "subject_name или subject_relation."
            )