"""
Модуль: memory/memory_manager.py

Управляет долговременной памятью пользователя через SQLAlchemy.
Применяет уже принятое решение памяти и не принимает решения
о сохранении информации самостоятельно.
"""

from __future__ import annotations

from datetime import datetime
from datetime import timezone
from typing import Optional

from sqlalchemy import select

from memory.database import get_session
from memory.models import PersonFact
from memory.models import RelatedPerson
from memory.models import Relation
from memory.models import User
from memory.models import UserFact


FACT_TYPE_SINGLE = "single"
FACT_TYPE_MULTI = "multi"
FACT_TYPE_TEMPORAL = "temporal"


FACT_TYPES = {
    "favorite_game": FACT_TYPE_SINGLE,
    "favorite_movie": FACT_TYPE_SINGLE,
    "favorite_music": FACT_TYPE_SINGLE,
    "favorite_book": FACT_TYPE_SINGLE,
    "favorite_food": FACT_TYPE_SINGLE,
    "hobby": FACT_TYPE_MULTI,
    "interest": FACT_TYPE_MULTI,

    "current_game": FACT_TYPE_TEMPORAL,
    "current_city": FACT_TYPE_TEMPORAL,
    "current_project": FACT_TYPE_TEMPORAL,
    "current_job": FACT_TYPE_TEMPORAL,
}


class MemoryManager:
    """
    Управляет долговременной памятью пользователя.

    MemoryManager отвечает только за корректное хранение,
    изменение, получение и удаление данных в базе.
    """

    def __init__(self):
        """Создаёт сессию SQLAlchemy для работы с долговременной памятью."""
        self.session = get_session()

    def close(self):
        """Закрывает текущую сессию базы данных."""
        self.session.close()

    def __enter__(self):
        """Возвращает MemoryManager для использования в контекстном менеджере."""
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        """Закрывает сессию после завершения работы с MemoryManager."""
        self.close()

    # ==========================================================
    # USER
    # ==========================================================

    def create_user(
        self,
        name: str,
        preferred_name: Optional[str] = None,
        language: str = "ru",
        country: Optional[str] = None,
        city: Optional[str] = None,
        timezone_name: Optional[str] = None,
        birth_date: Optional[str] = None,
        telegram_id: Optional[str] = None,
        telegram_username: Optional[str] = None,
        telegram_profile_url: Optional[str] = None,
    ) -> User:
        """Создаёт нового пользователя и сохраняет его в базе данных."""
        user = User(
            name=name,
            preferred_name=preferred_name,
            language=language,
            country=country,
            city=city,
            timezone=timezone_name,
            birth_date=birth_date,
            telegram_id=telegram_id,
            telegram_username=telegram_username,
            telegram_profile_url=telegram_profile_url,
        )

        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)

        return user

    def get_user(
        self,
        user_id: int,
    ) -> Optional[User]:
        """Возвращает пользователя по его ID или None, если пользователь не найден."""
        return self.session.get(
            User,
            user_id,
        )

    def update_user(
        self,
        user_id: int,
        **fields,
    ) -> User:
        """Обновляет разрешённые поля существующего пользователя."""
        user = self.get_user(
            user_id
        )

        if user is None:
            raise ValueError(
                f"Пользователь с id={user_id} не найден."
            )

        allowed_fields = {
            "name",
            "preferred_name",
            "language",
            "country",
            "city",
            "timezone",
            "birth_date",
            "telegram_id",
            "telegram_username",
            "telegram_profile_url",
        }

        for field, value in fields.items():
            if field not in allowed_fields:
                raise ValueError(
                    f"Поле '{field}' нельзя изменить."
                )

            setattr(
                user,
                field,
                value,
            )

        self.session.commit()
        self.session.refresh(user)

        return user

    # ==========================================================
    # USER FACTS
    # ==========================================================

    def remember_fact(
        self,
        user_id: int,
        category: str,
        key: str,
        value: str,
        source: str,
        confidence: float = 1.0,
        expires_at: Optional[datetime] = None,
    ) -> UserFact:
        """
        Сохраняет факт пользователя в долговременной памяти.

        Для single и temporal фактов предыдущая активная запись закрывается.
        """
        self._validate_confidence(
            confidence
        )

        if not value.strip():
            raise ValueError(
                "Значение факта не может быть пустым."
            )

        user = self.get_user(
            user_id
        )

        if user is None:
            raise ValueError(
                f"Пользователь с id={user_id} не найден."
            )

        fact_type = self._get_fact_type(
            key
        )

        if fact_type in {
            FACT_TYPE_SINGLE,
            FACT_TYPE_TEMPORAL,
        }:
            self._expire_existing_facts(
                user_id=user_id,
                category=category,
                key=key,
            )

        fact = UserFact(
            user_id=user_id,
            category=category,
            key=key,
            value=value,
            source=source,
            confidence=confidence,
            expires_at=expires_at,
        )

        self.session.add(fact)
        self.session.commit()
        self.session.refresh(fact)

        return fact

    def get_fact(
        self,
        user_id: int,
        category: str,
        key: str,
    ) -> Optional[UserFact]:
        """Возвращает один активный факт пользователя по категории и ключу."""
        now = self._now()

        statement = (
            select(UserFact)
            .where(
                UserFact.user_id == user_id,
                UserFact.category == category,
                UserFact.key == key,
                (
                    (UserFact.expires_at.is_(None))
                    | (UserFact.expires_at > now)
                ),
            )
            .order_by(
                UserFact.updated_at.desc()
            )
        )

        return self.session.scalars(
            statement
        ).first()

    def get_facts(
        self,
        user_id: int,
        category: Optional[str] = None,
        key: Optional[str] = None,
    ) -> list[UserFact]:
        """Возвращает все активные факты пользователя с необязательной фильтрацией."""
        now = self._now()

        conditions = [
            UserFact.user_id == user_id,
            (
                (UserFact.expires_at.is_(None))
                | (UserFact.expires_at > now)
            ),
        ]

        if category is not None:
            conditions.append(
                UserFact.category == category
            )

        if key is not None:
            conditions.append(
                UserFact.key == key
            )

        statement = (
            select(UserFact)
            .where(*conditions)
            .order_by(
                UserFact.updated_at.desc()
            )
        )

        return list(
            self.session.scalars(
                statement
            )
        )

    def update_fact(
        self,
        fact_id: int,
        value: str,
        confidence: Optional[float] = None,
        expires_at: Optional[datetime] = None,
    ) -> UserFact:
        """Обновляет значение, уверенность и срок действия существующего факта."""
        if not value.strip():
            raise ValueError(
                "Значение факта не может быть пустым."
            )

        fact = self.session.get(
            UserFact,
            fact_id,
        )

        if fact is None:
            raise ValueError(
                f"Факт с id={fact_id} не найден."
            )

        fact.value = value

        if confidence is not None:
            self._validate_confidence(
                confidence
            )
            fact.confidence = confidence

        fact.expires_at = expires_at

        self.session.commit()
        self.session.refresh(fact)

        return fact

    def forget_fact(
        self,
        fact_id: int,
    ):
        """Полностью удаляет факт пользователя из базы данных."""
        fact = self.session.get(
            UserFact,
            fact_id,
        )

        if fact is None:
            return

        self.session.delete(
            fact
        )
        self.session.commit()

    def expire_fact(
        self,
        fact_id: int,
    ):
        """Делает факт неактивным, сохраняя его историю в базе данных."""
        fact = self.session.get(
            UserFact,
            fact_id,
        )

        if fact is None:
            raise ValueError(
                f"Факт с id={fact_id} не найден."
            )

        fact.expires_at = self._now()

        self.session.commit()

    # ==========================================================
    # MEMORY DECISION
    # ==========================================================

    def apply_decision(
        self,
        user_id: int,
        memory: dict,
        source: str = "conversation",
    ):
        """
        Применяет решение Butler к долговременной памяти.

        В зависимости от subject_type изменяет память пользователя
        или память связанного человека.
        """
        action = memory["action"]

        if action == "ignore":
            return None

        subject_type = memory.get(
            "subject_type",
            "user",
        )

        if subject_type == "user":
            return self._apply_user_memory_decision(
                user_id=user_id,
                memory=memory,
                source=source,
            )

        if subject_type == "person":
            return self._apply_person_memory_decision(
                user_id=user_id,
                memory=memory,
                source=source,
            )

        raise ValueError(
            f"Неизвестный subject_type: {subject_type}"
        )

    def _apply_user_memory_decision(
        self,
        user_id: int,
        memory: dict,
        source: str,
    ):
        """Применяет решение памяти, относящееся к пользователю."""
        action = memory["action"]
        category = memory["category"]
        key = memory["key"]

        if category is None:
            raise ValueError(
                "Для решения памяти требуется category."
            )

        if key is None:
            raise ValueError(
                "Для решения памяти требуется key."
            )

        if action == "remember":
            value = memory["value"]

            if value is None:
                raise ValueError(
                    "Для remember требуется value."
                )

            return self.remember_fact(
                user_id=user_id,
                category=category,
                key=key,
                value=value,
                source=source,
                confidence=memory["confidence"],
            )

        if action == "forget":
            fact = self.get_fact(
                user_id=user_id,
                category=category,
                key=key,
            )

            if fact is None:
                return None

            self.forget_fact(
                fact.id
            )

            return fact

        raise ValueError(
            f"Неизвестное действие памяти: {action}"
        )

    def _apply_person_memory_decision(
        self,
        user_id: int,
        memory: dict,
        source: str,
    ):
        """Применяет решение памяти, относящееся к связанному человеку."""
        action = memory["action"]
        category = memory["category"]
        key = memory["key"]

        if category is None:
            raise ValueError(
                "Для решения памяти требуется category."
            )

        if key is None:
            raise ValueError(
                "Для решения памяти требуется key."
            )

        person = self._resolve_related_person(
            user_id=user_id,
            subject_name=memory.get(
                "subject_name"
            ),
            subject_relation=memory.get(
                "subject_relation"
            ),
        )

        if person is None:
            raise ValueError(
                "Не удалось определить связанного человека "
                "для решения памяти."
            )

        if action == "remember":
            value = memory["value"]

            if value is None:
                raise ValueError(
                    "Для remember требуется value."
                )

            return self.remember_person_fact(
                related_person_id=person.id,
                category=category,
                key=key,
                value=value,
                source=source,
                confidence=memory["confidence"],
            )

        if action == "forget":
            fact = self.get_person_fact(
                related_person_id=person.id,
                category=category,
                key=key,
            )

            if fact is None:
                return None

            self.forget_person_fact(
                fact.id
            )

            return fact

        raise ValueError(
            f"Неизвестное действие памяти: {action}"
        )

    # ==========================================================
    # RELATED PEOPLE
    # ==========================================================

    def add_person(
        self,
        user_id: int,
        name: str,
        preferred_name: Optional[str] = None,
    ) -> RelatedPerson:
        """Добавляет связанного с пользователем человека."""
        user = self.get_user(
            user_id
        )

        if user is None:
            raise ValueError(
                f"Пользователь с id={user_id} не найден."
            )

        person = RelatedPerson(
            user_id=user_id,
            name=name,
            preferred_name=preferred_name,
        )

        self.session.add(person)
        self.session.commit()
        self.session.refresh(person)

        return person

    def get_person(
        self,
        person_id: int,
    ) -> Optional[RelatedPerson]:
        """Возвращает связанного человека по его ID."""
        return self.session.get(
            RelatedPerson,
            person_id,
        )

    def get_people(
        self,
        user_id: int,
    ) -> list[RelatedPerson]:
        """Возвращает всех людей, связанных с указанным пользователем."""
        statement = (
            select(RelatedPerson)
            .where(
                RelatedPerson.user_id == user_id
            )
            .order_by(
                RelatedPerson.name
            )
        )

        return list(
            self.session.scalars(
                statement
            )
        )

    def add_relation(
        self,
        user_id: int,
        related_person_id: int,
        relation_type: str,
        source: str,
        confidence: float = 1.0,
    ) -> Relation:
        """Создаёт связь между пользователем и принадлежащим ему человеком."""
        self._validate_confidence(
            confidence
        )

        person = self.get_person(
            related_person_id
        )

        if person is None:
            raise ValueError(
                f"Человек с id={related_person_id} "
                f"не найден."
            )

        if person.user_id != user_id:
            raise ValueError(
                "Человек не принадлежит указанному "
                "пользователю."
            )

        relation = Relation(
            user_id=user_id,
            related_person_id=related_person_id,
            relation_type=relation_type,
            source=source,
            confidence=confidence,
        )

        self.session.add(
            relation
        )
        self.session.commit()
        self.session.refresh(
            relation
        )

        return relation

    def get_relations(
        self,
        user_id: int,
    ) -> list[Relation]:
        """Возвращает все связи указанного пользователя."""
        statement = (
            select(Relation)
            .where(
                Relation.user_id == user_id
            )
            .order_by(
                Relation.updated_at.desc()
            )
        )

        return list(
            self.session.scalars(
                statement
            )
        )

    # ==========================================================
    # PERSON FACTS
    # ==========================================================

    def remember_person_fact(
        self,
        related_person_id: int,
        category: str,
        key: str,
        value: str,
        source: str,
        confidence: float = 1.0,
        expires_at: Optional[datetime] = None,
    ) -> PersonFact:
        """
        Сохраняет факт о связанном человеке.

        Для single и temporal фактов предыдущая активная запись закрывается.
        """
        self._validate_confidence(
            confidence
        )

        if not value.strip():
            raise ValueError(
                "Значение факта не может быть пустым."
            )

        person = self.get_person(
            related_person_id
        )

        if person is None:
            raise ValueError(
                f"Человек с id={related_person_id} "
                f"не найден."
            )

        fact_type = self._get_fact_type(
            key
        )

        if fact_type in {
            FACT_TYPE_SINGLE,
            FACT_TYPE_TEMPORAL,
        }:
            self._expire_existing_person_facts(
                related_person_id=related_person_id,
                category=category,
                key=key,
            )

        fact = PersonFact(
            related_person_id=related_person_id,
            category=category,
            key=key,
            value=value,
            source=source,
            confidence=confidence,
            expires_at=expires_at,
        )

        self.session.add(
            fact
        )
        self.session.commit()
        self.session.refresh(
            fact
        )

        return fact

    def get_person_fact(
        self,
        related_person_id: int,
        category: str,
        key: str,
    ) -> Optional[PersonFact]:
        """Возвращает один активный факт о связанном человеке."""
        now = self._now()

        statement = (
            select(PersonFact)
            .where(
                PersonFact.related_person_id
                == related_person_id,
                PersonFact.category
                == category,
                PersonFact.key
                == key,
                (
                    (PersonFact.expires_at.is_(None))
                    | (PersonFact.expires_at > now)
                ),
            )
            .order_by(
                PersonFact.updated_at.desc()
            )
        )

        return self.session.scalars(
            statement
        ).first()

    def get_person_facts(
        self,
        related_person_id: int,
        category: Optional[str] = None,
        key: Optional[str] = None,
    ) -> list[PersonFact]:
        """Возвращает активные факты о связанном человеке с необязательной фильтрацией."""
        now = self._now()

        conditions = [
            PersonFact.related_person_id
            == related_person_id,
            (
                (PersonFact.expires_at.is_(None))
                | (PersonFact.expires_at > now)
            ),
        ]

        if category is not None:
            conditions.append(
                PersonFact.category == category
            )

        if key is not None:
            conditions.append(
                PersonFact.key == key
            )

        statement = (
            select(PersonFact)
            .where(*conditions)
            .order_by(
                PersonFact.updated_at.desc()
            )
        )

        return list(
            self.session.scalars(
                statement
            )
        )

    def forget_person_fact(
        self,
        fact_id: int,
    ):
        """Полностью удаляет факт связанного человека из базы данных."""
        fact = self.session.get(
            PersonFact,
            fact_id,
        )

        if fact is None:
            return

        self.session.delete(
            fact
        )
        self.session.commit()

    # ==========================================================
    # INTERNAL
    # ==========================================================

    def _resolve_related_person(
        self,
        user_id: int,
        subject_name: Optional[str],
        subject_relation: Optional[str],
    ) -> Optional[RelatedPerson]:
        """
        Определяет связанного человека по имени или отношению.

        Если по отношению найдено несколько людей, метод не выбирает
        человека случайно и возвращает None.
        """
        people = self.get_people(
            user_id
        )

        if subject_name:
            normalized_name = subject_name.strip().lower()

            for person in people:
                names = {
                    person.name.strip().lower(),
                }

                if person.preferred_name:
                    names.add(
                        person.preferred_name.strip().lower()
                    )

                if normalized_name in names:
                    return person

        if subject_relation:
            relations = self.get_relations(
                user_id
            )

            matches = []

            normalized_relation = (
                subject_relation.strip().lower()
            )

            for relation in relations:
                if (
                    relation.relation_type.strip().lower()
                    != normalized_relation
                ):
                    continue

                person = self.get_person(
                    relation.related_person_id
                )

                if person is not None:
                    matches.append(
                        person
                    )

            if len(matches) == 1:
                return matches[0]

        return None

    def _get_fact_type(
        self,
        key: str,
    ) -> str:
        """Возвращает тип факта по его ключу или использует multi по умолчанию."""
        return FACT_TYPES.get(
            key,
            FACT_TYPE_MULTI,
        )

    def _expire_existing_facts(
        self,
        user_id: int,
        category: str,
        key: str,
    ):
        """Закрывает все активные факты пользователя с указанными категорией и ключом."""
        statement = (
            select(UserFact)
            .where(
                UserFact.user_id == user_id,
                UserFact.category == category,
                UserFact.key == key,
                UserFact.expires_at.is_(None),
            )
        )

        facts = self.session.scalars(
            statement
        ).all()

        now = self._now()

        for fact in facts:
            fact.expires_at = now

    def _expire_existing_person_facts(
        self,
        related_person_id: int,
        category: str,
        key: str,
    ):
        """Закрывает активные факты связанного человека с указанными категорией и ключом."""
        statement = (
            select(PersonFact)
            .where(
                PersonFact.related_person_id
                == related_person_id,
                PersonFact.category
                == category,
                PersonFact.key
                == key,
                PersonFact.expires_at.is_(None),
            )
        )

        facts = self.session.scalars(
            statement
        ).all()

        now = self._now()

        for fact in facts:
            fact.expires_at = now

    @staticmethod
    def _now() -> datetime:
        """Возвращает текущее время в UTC без timezone-информации для SQLite."""
        return datetime.now(
            timezone.utc
        ).replace(
            tzinfo=None
        )

    @staticmethod
    def _validate_confidence(
        confidence: float,
    ):
        """Проверяет, что confidence находится в диапазоне от 0.0 до 1.0."""
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(
                "confidence должен находиться "
                "в диапазоне от 0.0 до 1.0."
            )