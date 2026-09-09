"""
Модуль: main.py

Главная точка входа голосового ассистента Nova.
Связывает распознавание речи, Context Manager, Butler, память,
выполнение команд, Responder и синтез речи в единый цикл.
"""

import os
import time

from sqlalchemy import select

from ai.butler import Butler
from ai.responder import Responder
from commands.handler import CommandHandler
from logger import get_logger
from memory.context_manager import ContextManager
from memory.database import get_session
from memory.database import init_database
from memory.memory_manager import MemoryManager
from memory.models import User
from speech.recognizer import SpeechRecognizer
from speech.synthesizer import SpeechSynthesizer


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

log = get_logger("MAIN")

TTS_COOLDOWN = 0.5


def get_default_user_id() -> int:
    """Возвращает ID первого пользователя, сохранённого в базе данных."""
    with get_session() as session:
        user = session.scalars(
            select(User)
            .order_by(User.id)
        ).first()

        if user is None:
            raise RuntimeError(
                "В базе данных нет пользователей. "
                "Сначала запусти seed_memory.py."
            )

        return user.id


def main():
    """Запускает голосового ассистента и обрабатывает сообщения пользователя."""
    print("=" * 60)
    print("                    NOVA")
    print("=" * 60)

    log.info("Запуск голосового помощника Nova")
    log.info("Инициализация компонентов")

    init_database()

    user_id = get_default_user_id()

    log.info(
        "Используется пользователь с ID: {}",
        user_id,
    )

    memory_manager = MemoryManager()
    log.info("MemoryManager инициализирован")

    context_manager = ContextManager()
    log.info("ContextManager инициализирован")

    recognizer = SpeechRecognizer()
    log.info("SpeechRecognizer инициализирован")

    butler = Butler()
    log.info("Butler инициализирован")

    handler = CommandHandler()
    log.info("CommandHandler инициализирован")

    responder = Responder()
    log.info("Responder инициализирован")

    synthesizer = SpeechSynthesizer()
    log.info("SpeechSynthesizer инициализирован")

    log.info("Все компоненты загружены")

    print("\n" + "=" * 60)
    print("ГОТОВО")
    print("=" * 60)

    print("\nГовори с Nova.")
    print("Для выхода нажми Ctrl+C.\n")

    while True:
        audio = recognizer.record_phrase()

        if audio is None:
            log.debug("Запись отсутствует")
            continue

        text = recognizer.recognize(audio)

        if not text:
            log.debug("Whisper не распознал текст")
            continue

        print(f"\n📝 Ты: {text}")

        log.info(
            "Получен текст пользователя: {}",
            text,
        )

        try:
            context = context_manager.build_context(
                user_id=user_id,
                text=text,
            )
        except Exception:
            log.exception(
                "Ошибка при формировании контекста",
            )

            context = {}

            print(
                "\n⚠️ Не удалось загрузить память. "
                "Продолжаю без контекста."
            )

        log.debug(
            "Контекст пользователя: {}",
            context,
        )

        try:
            command_data = butler.analyze(
                text=text,
                context=context,
            )
        except Exception:
            log.exception(
                "Ошибка при обработке сообщения Butler",
            )

            print(
                "\n❌ Не удалось обработать запрос. "
                "Подробности находятся в logs/assistant.log"
            )

            continue

        log.info(
            "Butler определил команду: {}",
            command_data["command"],
        )

        log.debug(
            "Данные Butler: {}",
            command_data,
        )

        memory_decision = command_data.get("memory")

        if memory_decision:
            try:
                memory_manager.apply_decision(
                    user_id=user_id,
                    memory=memory_decision,
                    source="conversation",
                )

                log.info(
                    "Решение по памяти обработано: {}",
                    memory_decision.get("action"),
                )

            except Exception:
                log.exception(
                    "Ошибка при сохранении решения Butler в память",
                )

                print(
                    "\n⚠️ Не удалось обновить память. "
                    "Продолжаю обработку запроса."
                )

        try:
            command_data = handler.execute(
                command_data,
            )

        except Exception:
            log.exception(
                "Ошибка при выполнении команды",
            )

            print(
                "\n❌ Не удалось выполнить команду. "
                "Подробности находятся в logs/assistant.log"
            )

            continue

        log.info(
            "Команда успешно выполнена",
        )

        log.debug(
            "Результат выполнения команды: {}",
            command_data.get("result"),
        )

        try:
            answer = responder.respond(
                data=command_data,
                context=context,
            )

        except Exception:
            log.exception(
                "Ошибка при формировании ответа Responder",
            )

            print(
                "\n❌ Не удалось сформировать ответ. "
                "Подробности находятся в logs/assistant.log"
            )

            continue

        log.info(
            "Responder сформировал ответ",
        )

        log.debug(
            "Ответ Responder: {}",
            answer,
        )

        print(f"\n🤖 Nova: {answer}")

        try:
            synthesizer.speak(answer)
            time.sleep(TTS_COOLDOWN)

        except Exception:
            log.exception(
                "Ошибка при озвучивании ответа",
            )

            print(
                "\n⚠️ Не удалось озвучить ответ. "
                "Продолжаю работу в текстовом режиме."
            )

        log.info(
            "Ответ отправлен пользователю",
        )


if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        log.info(
            "Ассистент остановлен пользователем",
        )

        print(
            "\n\nПрограмма завершена."
        )

    except Exception:
        log.exception(
            "Критическая ошибка ассистента",
        )

        print(
            "\n❌ Произошла критическая ошибка. "
            "Подробности находятся в logs/assistant.log"
        )