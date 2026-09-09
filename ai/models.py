"""
Модуль: ai/models.py

Содержит модели и фабрику для работы с LLM-провайдерами.
Поддерживает OpenRouter и локальный OpenAI-compatible сервер llama.cpp.
"""

from typing import Any

from openai import OpenAI

from config import MODELS
from config import OPENROUTER_BASE_URL
from config import OPENROUTER_API_KEY


BUTLER_SCHEMA = {
    "name": "butler_response",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "enum": [
                    "conversation",
                    "weather",
                    "music",
                ],
            },
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": [
                            "string",
                            "null",
                        ],
                    },
                    "city": {
                        "type": [
                            "string",
                            "null",
                        ],
                    },
                    "query": {
                        "type": [
                            "string",
                            "null",
                        ],
                    },
                },
                "required": [
                    "text",
                    "city",
                    "query",
                ],
                "additionalProperties": False,
            },
            "memory": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "remember",
                            "forget",
                            "ignore",
                        ],
                    },
                    "category": {
                        "type": [
                            "string",
                            "null",
                        ],
                    },
                    "key": {
                        "type": [
                            "string",
                            "null",
                        ],
                    },
                    "value": {
                        "type": [
                            "string",
                            "null",
                        ],
                    },
                    "confidence": {
                        "type": "number",
                    },
                },
                "required": [
                    "action",
                    "category",
                    "key",
                    "value",
                    "confidence",
                ],
                "additionalProperties": False,
            },
            "result": {
                "type": [
                    "string",
                    "null",
                ],
            },
            "prompt": {
                "type": "string",
            },
        },
        "required": [
            "command",
            "parameters",
            "memory",
            "result",
            "prompt",
        ],
        "additionalProperties": False,
    },
}


class OpenRouterModel:
    """Предоставляет доступ к моделям OpenRouter через OpenAI-compatible API."""

    def __init__(
        self,
        model: str,
        fallback_models: list[str] | None = None,
    ):
        """Создаёт клиент OpenRouter с основной моделью и списком резервных моделей."""
        self.model = model
        self.fallback_models = fallback_models or []

        self.client = OpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,
        )

    def ask(self, prompt: str) -> str:
        """Отправляет обычный текстовый запрос в OpenRouter и возвращает ответ модели."""
        models = [
            self.model,
            *self.fallback_models,
        ]

        last_error = None

        for model in models:
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                )

                return response.choices[0].message.content or ""

            except Exception as error:
                last_error = error

        if last_error is not None:
            raise last_error

        raise RuntimeError(
            "Не удалось выполнить запрос к OpenRouter."
        )

    def ask_json(self, prompt: str) -> str:
        """Отправляет запрос в OpenRouter с обязательным структурированным JSON-ответом."""
        models = [
            self.model,
            *self.fallback_models,
        ]

        last_error = None

        for model in models:
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                    response_format={
                        "type": "json_schema",
                        "json_schema": BUTLER_SCHEMA,
                    },
                )

                return response.choices[0].message.content or ""

            except Exception as error:
                last_error = error

        if last_error is not None:
            raise last_error

        raise RuntimeError(
            "Не удалось выполнить JSON-запрос к OpenRouter."
        )


class LocalModel:
    """Предоставляет доступ к локальной модели через OpenAI-compatible API llama.cpp."""

    def __init__(
        self,
        model: str,
        base_url: str,
        api_key: str,
    ):
        """Создаёт клиента для локального OpenAI-compatible сервера."""
        self.model = model

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )

    def ask(self, prompt: str) -> str:
        """Отправляет обычный запрос локальной модели и возвращает текстовый ответ."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        return response.choices[0].message.content or ""

    def ask_json(self, prompt: str) -> str:
        """Отправляет запрос локальной модели с требованием вернуть JSON заданной схемы."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            response_format={
                "type": "json_schema",
                "json_schema": BUTLER_SCHEMA,
            },
        )

        return response.choices[0].message.content or ""


class ModelFactory:
    """Создаёт экземпляр модели на основе конфигурации выбранного провайдера."""

    @staticmethod
    def create(model_name: str) -> Any:
        """Возвращает настроенный объект модели из конфигурации приложения."""
        if model_name not in MODELS:
            raise ValueError(
                f"Модель '{model_name}' "
                f"не найдена в MODELS."
            )

        config = MODELS[model_name]

        provider = config["provider"]

        if provider == "openrouter":
            return OpenRouterModel(
                model=config["model"],
                fallback_models=config.get(
                    "fallback_models",
                    [],
                ),
            )

        if provider == "local":
            return LocalModel(
                model=config["model"],
                base_url=config["base_url"],
                api_key=config["api_key"],
            )

        raise ValueError(
            f"Неизвестный provider: {provider}"
        )