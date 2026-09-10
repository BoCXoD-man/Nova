"""
Реестр инструментов Nova.

Хранит зарегистрированные инструменты и предоставляет функции
для их регистрации и получения по имени.
"""

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Tool:
    """Описывает зарегистрированный инструмент Nova."""

    name: str
    description: str
    function: Callable[..., Any]


_tools: dict[str, Tool] = {}


def register_tool(
    name: str,
    description: str,
):
    """Регистрирует функцию как инструмент Nova."""

    def decorator(function: Callable[..., Any]):
        """Создаёт описание инструмента и добавляет его в реестр."""

        if name in _tools:
            raise ValueError(
                f"Инструмент '{name}' уже зарегистрирован."
            )

        _tools[name] = Tool(
            name=name,
            description=description,
            function=function,
        )

        return function

    return decorator


def get_tool(name: str) -> Tool:
    """Возвращает зарегистрированный инструмент по его имени."""

    try:
        return _tools[name]
    except KeyError:
        raise ValueError(
            f"Инструмент '{name}' не найден."
        )


def get_tools() -> list[Tool]:
    """Возвращает список всех зарегистрированных инструментов."""

    return list(_tools.values())