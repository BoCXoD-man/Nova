"""
Модуль: memory/context_manager.py

Формирует актуальный контекст пользователя для обработки текущего запроса.
Извлекает только релевантные данные из профиля, фактов и отношений,
не передавая модели всю базу данных целиком.
"""

from sqlalchemy import select

from memory.database import get_session
from memory.models import RelatedPerson
from memory.models import Relation
from memory.models import User
from memory.models import UserFact

from logger import get_logger


log = get_logger("CONTEXT")


class ContextManager:
    """Формирует релевантный контекст пользователя для текущего запроса."""

    PROFILE_KEYWORDS = {
        "имя",
        "зовут",
        "называть",
        "меня",
        "кто я",
    }

    GAME_KEYWORDS = {
        "игра",
        "играю",
        "играл",
        "играла",
        "любимая игра",
        "любимый",
        "любимая",
        "игр",
    }

    HOBBY_KEYWORDS = {
        "хобби",
        "интерес",
        "увлечени",
        "нравится",
    }

    RELATION_KEYWORDS = {
        "жена",
        "муж",
        "дочь",
        "сын",
        "мама",
        "мать",
        "отец",
        "папа",
        "брат",
        "сестра",
        "друг",
        "друзья",
        "семья",
        "родствен",
    }

    def __init__(self):
        """Инициализирует Context Manager."""
        log.info("ContextManager инициализирован")

    def build_context(
        self,
        user_id: int,
        text: str,
    ) -> dict:
        """Формирует релевантный контекст пользователя для текущего сообщения."""
        normalized_text = text.lower()

        context = {
            "profile": None,
            "facts": [],
            "relations": [],
        }

        with get_session() as session:
            user = session.get(User, user_id)

            if user is None:
                log.warning(
                    "Пользователь с ID {} не найден",
                    user_id,
                )
                return context

            context["profile"] = self._build_profile(user)

            facts = self._get_relevant_facts(
                session=session,
                user_id=user_id,
                text=normalized_text,
            )

            context["facts"] = facts

            relations = self._get_relevant_relations(
                session=session,
                user_id=user_id,
                text=normalized_text,
            )

            context["relations"] = relations

        log.debug(
            "Контекст сформирован: профиль={}, фактов={}, отношений={}",
            context["profile"] is not None,
            len(context["facts"]),
            len(context["relations"]),
        )

        return context

    def _build_profile(self, user: User) -> dict:
        """Преобразует профиль пользователя в словарь для передачи модели."""
        return {
            "name": user.name,
            "preferred_name": user.preferred_name,
            "language": user.language,
            "country": user.country,
            "city": user.city,
            "timezone": user.timezone,
        }

    def _get_relevant_facts(
        self,
        session,
        user_id: int,
        text: str,
    ) -> list[dict]:
        """Возвращает только факты, относящиеся к текущему запросу."""
        result = session.execute(
            select(UserFact)
            .where(UserFact.user_id == user_id)
            .where(UserFact.expires_at.is_(None))
        )

        facts = result.scalars().all()

        if self._contains_any(text, self.GAME_KEYWORDS):
            return [
                self._serialize_fact(fact)
                for fact in facts
                if fact.key in {
                    "favorite_game",
                    "current_game",
                }
            ]

        if self._contains_any(text, self.HOBBY_KEYWORDS):
            return [
                self._serialize_fact(fact)
                for fact in facts
                if fact.category in {
                    "interests",
                }
                or fact.key in {
                    "hobby",
                    "interest",
                }
            ]

        return []

    def _get_relevant_relations(
        self,
        session,
        user_id: int,
        text: str,
    ) -> list[dict]:
        """Возвращает отношения пользователя, если запрос касается людей."""
        if not self._contains_any(text, self.RELATION_KEYWORDS):
            return []

        result = session.execute(
            select(Relation, RelatedPerson)
            .join(
                RelatedPerson,
                Relation.related_person_id == RelatedPerson.id,
            )
            .where(Relation.user_id == user_id)
        )

        relations = []

        for relation, person in result.all():
            relations.append(
                {
                    "person": person.name,
                    "preferred_name": person.preferred_name,
                    "relation": relation.relation_type,
                    "confidence": relation.confidence,
                }
            )

        return relations

    @staticmethod
    def _serialize_fact(fact: UserFact) -> dict:
        """Преобразует объект UserFact в словарь."""
        return {
            "category": fact.category,
            "key": fact.key,
            "value": fact.value,
            "confidence": fact.confidence,
        }

    @staticmethod
    def _contains_any(
        text: str,
        keywords: set[str],
    ) -> bool:
        """Проверяет, содержит ли текст хотя бы одно ключевое слово."""
        return any(
            keyword in text
            for keyword in keywords
        )