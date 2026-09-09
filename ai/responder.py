"""
Модуль: ai/responder.py

Responder формирует естественный ответ пользователю на основе
результата выполнения команды и релевантного контекста пользователя.
"""

import json

from ai.models import ModelFactory
from config import RESPONDER_MODEL

from logger import get_logger


log = get_logger("RESPONDER")


RESPONDER_PROMPT = """
Ты — Responder голосового ассистента Алиса.

Твоя задача — сформировать естественный ответ
пользователю на основе данных, которые передал Butler.

Отвечай только пользователю.

Не упоминай:
- Butler
- JSON
- Handler
- Context Manager
- Memory Manager
- модели
- программный код
- внутреннюю архитектуру ассистента.

Отвечай на русском языке.

Будь естественной и краткой.

Если вопрос простой — ответь коротко.

Если требуется объяснение — объясни подробно.

Не выдумывай информацию.

КОНТЕКСТ ПОЛЬЗОВАТЕЛЯ:

Контекст содержит информацию, ранее сохранённую
о пользователе.

Если пользователь спрашивает о себе,
используй информацию из контекста.

Например:

"Как меня зовут?"
→ используй profile.name или profile.preferred_name.

"Как меня называть?"
→ используй profile.preferred_name.

"Какая моя любимая игра?"
→ используй факт favorite_game.

"Во что я сейчас играю?"
→ используй факт current_game.

"Какие у меня хобби?"
→ используй соответствующие факты.

"Кто моя жена?"
→ используй relations.

ВАЖНО:

Если нужной информации нет в контексте,
не выдумывай её.

Если вопрос не связан с информацией о пользователе,
контекст можно игнорировать.

КОМАНДЫ:

Если command = conversation,
используй parameters.text и контекст пользователя.

Если command = weather,
используй данные о погоде только из result.

Если command = music,
используй результат выполнения команды
и сообщи пользователю о результате.

Если result содержит ошибку,
сообщи пользователю об ошибке естественным языком.

Не используй Markdown без необходимости.

Верни только готовый текст ответа пользователю.
"""


class Responder:
    """Формирует естественный ответ пользователю на основе данных Butler."""

    def __init__(self):
        """Инициализирует Responder и подключает выбранную модель."""
        log.info(
            "Инициализация Responder. Модель: {}",
            RESPONDER_MODEL,
        )

        self.ai = ModelFactory.create(RESPONDER_MODEL)

        log.info(
            "Responder успешно инициализирован",
        )

    def respond(
        self,
        data: dict,
        context: dict | None = None,
    ) -> str:
        """Формирует ответ пользователю с учётом релевантного контекста."""
        context = context or {}

        prompt = data.get("prompt", "")
        command = data.get("command", "")
        parameters = data.get("parameters", {})
        result = data.get("result", None)

        response_data = {
            "command": command,
            "parameters": parameters,
            "result": result,
            "prompt": prompt,
            "context": context,
        }

        serialized_data = json.dumps(
            response_data,
            ensure_ascii=False,
            indent=4,
        )

        user_prompt = f"""
{RESPONDER_PROMPT}

Инструкция Butler:

{prompt}

Данные команды и контекст:

{serialized_data}

Сформируй итоговый ответ пользователю.
"""

        log.info(
            "Responder формирует ответ. Команда: {}",
            command,
        )

        try:
            answer = self.ai.ask(
                user_prompt,
            )
        except Exception:
            log.exception(
                "Ошибка при запросе к модели Responder",
            )
            raise

        if not answer:
            raise RuntimeError(
                "Responder вернул пустой ответ."
            )

        answer = answer.strip()

        log.debug(
            "Ответ Responder: {}",
            answer,
        )

        return answer