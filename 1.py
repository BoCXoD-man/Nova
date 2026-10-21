"""
Одноразовое исправление города пользователя в памяти Nova.

Находит пользователя Андрея и заменяет сохранённый город
«Батуме» на корректное название «Батуми».
"""

from memory.database import SessionLocal
from memory.models import User


def fix_city() -> None:
    """Исправляет сохранённое название города пользователя."""

    with SessionLocal() as session:
        users = session.query(User).all()

        if not users:
            print("Пользователи в базе не найдены.")
            return

        for user in users:
            print(
                f"Пользователь: {user.name}, "
                f"город: {user.city}"
            )

        user = next(
            (
                user
                for user in users
                if user.name == "Андрей"
            ),
            None,
        )

        if user is None:
            print("Пользователь Андрей не найден.")
            return

        if user.city == "Батуми":
            print("Город уже указан правильно: Батуми.")
            return

        if user.city != "Батуме":
            print(
                f"Неожиданное значение города: {user.city!r}"
            )
            return

        user.city = "Батуми"
        session.commit()

        print("Город успешно изменён: Батуме → Батуми")


if __name__ == "__main__":
    fix_city()

