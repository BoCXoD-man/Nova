import json

from ai.models import ModelFactory
from config import BUTLER_MODEL
from memory.schema import MemoryDecision

from logger import get_logger


log = get_logger("MEMORY_AI")


MEMORY_PROMPT = """
Ты — Memory Analyzer голосового ассистента Алиса.

Твоя задача — определить, содержит ли сообщение пользователя
информацию, которую имеет смысл сохранить в долговременной памяти.

Ты НЕ должен отвечать пользователю.

Ты должен вернуть строго JSON.

Допустимые действия:

1. remember

Используй, если пользователь сообщает устойчивую,
полезную для будущих разговоров информацию о себе,
своих предпочтениях, интересах, работе, текущих занятиях
или других важных фактах.

Пример:

Пользователь:
"Мне нравится Baldur's Gate 3"

Ответ:

{
    "action": "remember",
    "category": "interests",
    "key": "favorite_game",
    "value": "Baldur's Gate 3",
    "confidence": 0.95,
    "reason": "Пользователь сообщил о своей любимой игре."
}

2. forget

Используй, если пользователь явно просит забыть
ранее сохранённую информацию.

Пример:

Пользователь:
"Забудь, что моя любимая игра Baldur's Gate 3"

Ответ:

{
    "action": "forget",
    "category": "interests",
    "key": "favorite_game",
    "value": null,
    "confidence": 1.0,
    "reason": "Пользователь явно попросил забыть информацию."
}

3. ignore

Используй для информации, которую не нужно сохранять.

Например:

"Какая сегодня погода?"

"Что такое Python?"

"Запусти музыку."

"Привет."

Также не сохраняй случайные, одноразовые фразы,
если они не имеют очевидной долгосрочной ценности.

ВАЖНЫЕ ПРАВИЛА:

- Не сохраняй каждый факт подряд.
- Сохраняй только информацию, которая может быть полезна
  в будущих разговорах.
- Не выдумывай информацию.
- value должен содержать только информацию,
  которую непосредственно сообщил пользователь.
- confidence должен отражать уверенность в том,
  что пользователь действительно сообщил этот факт.
- Для изменения существующего факта используй remember.
  MemoryManager сам обработает замену старого значения.
- Если пользователь говорит "теперь", "больше не", "уже",
  "сейчас", учитывай изменение состояния.
- Не сохраняй ответы самого ассистента.
- Не сохраняй технические детали текущего запроса,
  если они не являются устойчивой информацией о пользователе.

Категории:

interests
preferences
work
location
activity
personal
relations

Примеры ключей:

favorite_game
favorite_movie
favorite_music
favorite_book
hobby
interest
occupation
current_job
current_game
current_project
current_city

Для отношений с людьми пока НЕ используй remember.
Отношения будут обрабатываться отдельным механизмом.

Если информации для сохранения нет:

{
    "action": "ignore",
    "category": null,
    "key": null,
    "value": null,
    "confidence": 1.0,
    "reason": "В сообщении нет долговременной информации."
}

Никогда не добавляй текст вне JSON.
"""


class MemoryAnalyzer:
    def __init__(self):
        log.info(
            "Инициализация MemoryAnalyzer. Модель: {}",
            BUTLER_MODEL,
        )

        self.ai = ModelFactory.create(BUTLER_MODEL)

        log.info(
            "MemoryAnalyzer успешно инициализирован"
        )

    def analyze(self, text: str) -> MemoryDecision:
        log.info(
            "Анализ сообщения на наличие данных для памяти"
        )

        response = self.ai.ask_json(
            f"""
{MEMORY_PROMPT}

Сообщение пользователя:

{text}
"""
        )

        log.debug(
            "Ответ MemoryAnalyzer: {}",
            response,
        )

        try:
            data = json.loads(response)

        except json.JSONDecodeError as error:
            log.error(
                "MemoryAnalyzer вернул некорректный JSON: {}",
                response,
            )

            raise ValueError(
                "MemoryAnalyzer вернул некорректный JSON."
            ) from error

        try:
            decision = MemoryDecision.model_validate(
                data
            )

        except Exception as error:
            log.error(
                "Некорректное решение MemoryAnalyzer: {}",
                data,
            )

            raise ValueError(
                "MemoryAnalyzer вернул некорректное "
                "решение памяти."
            ) from error

        log.info(
            "Решение памяти: {}",
            decision.action,
        )

        return decision