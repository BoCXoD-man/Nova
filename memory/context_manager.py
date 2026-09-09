"""
Модуль: memory/context_manager.py

Формирует релевантный контекст пользователя для текущего запроса.
Определяет, относится ли запрос к самому пользователю или к связанному
с ним человеку, и извлекает только необходимые данные из памяти.
"""

from sqlalchemy import select

from logger import get_logger
from memory.database import get_session
from memory.models import PersonFact
from memory.models import RelatedPerson
from memory.models import Relation
from memory.models import User
from memory.models import UserFact


log = get_logger("CONTEXT")


class ContextManager:
    """Формирует релевантный контекст пользователя для текущего запроса."""

    RELATION_KEYWORDS = {
        "жена": "wife",
        "жену": "wife",
        "жене": "wife",
        "муж": "husband",
        "мужа": "husband",
        "мужу": "husband",
        "дочь": "daughter",
        "дочери": "daughter",
        "дочь": "daughter",
        "сын": "son",
        "сына": "son",
        "мама": "mother",
        "маму": "mother",
        "мат": "mother",
        "мать": "mother",
        "папа": "father",
        "папу": "father",
        "отец": "father",
        "брата": "brother",
        "брат": "brother",
        "сестра": "sister",
        "сестру": "sister",
        "друг": "friend",
        "друга": "friend",
        "друзья": "friend",
    }

    GAME_KEYWORDS = {
        "игра",
        "играю",
        "играл",
        "играла",
        "игр",
        "любимая игра",
        "любимый",
        "любимая",
    }

    HOBBY_KEYWORDS = {
        "хобби",
        "интерес",
        "увлечени",
        "нравится",
    }

    PROFILE_KEYWORDS = {
        "имя",
        "зовут",
        "называть",
        "меня",
        "кто я",
    }

    PERSON_FACT_KEYWORDS = {
        "любит",
        "нравится",
        "любим",
        "предпочитает",
        "хочет",
        "играет",
        "работает",
        "учится",
        "возраст",
        "день рождения",
        "еда",
        "любимая еда",
        "хобби",
        "интерес",
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
        normalized_text = text.lower().strip()

        context = {
            "profile": None,
            "facts": [],
            "relations": [],
            "person": None,
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

            context["facts"] = self._get_relevant_user_facts(
                session=session,
                user_id=user_id,
                text=normalized_text,
            )

            person_data = self._get_relevant_person(
                session=session,
                user_id=user_id,
                text=normalized_text,
            )

            if person_data is not None:
                context["person"] = person_data

            context["relations"] = self._get_relevant_relations(
                session=session,
                user_id=user_id,
                text=normalized_text,
            )

        log.debug(
            "Контекст сформирован: профиль={}, фактов={}, "
            "отношений={}, person={}",
            context["profile"] is not None,
            len(context["facts"]),
            len(context["relations"]),
            context["person"] is not None,
        )

        return context

    def _build_profile(
        self,
        user: User,
    ) -> dict:
        """Преобразует профиль пользователя в словарь."""
        return {
            "name": user.name,
            "preferred_name": user.preferred_name,
            "language": user.language,
            "country": user.country,
            "city": user.city,
            "timezone": user.timezone,
        }

    def _get_relevant_user_facts(
        self,
        session,
        user_id: int,
        text: str,
    ) -> list[dict]:
        """Возвращает релевантные факты самого пользователя."""
        result = session.execute(
            select(UserFact)
            .where(UserFact.user_id == user_id)
            .where(UserFact.expires_at.is_(None))
        )

        facts = result.scalars().all()

        if self._contains_any(text, self.GAME_KEYWORDS):
            return [
                self._serialize_user_fact(fact)
                for fact in facts
                if fact.key in {
                    "favorite_game",
                    "current_game",
                }
            ]

        if self._contains_any(text, self.HOBBY_KEYWORDS):
            return [
                self._serialize_user_fact(fact)
                for fact in facts
                if fact.category == "interests"
                or fact.key in {
                    "hobby",
                    "interest",
                }
            ]

        if self._contains_any(text, self.PROFILE_KEYWORDS):
            return []

        return []

    def _get_relevant_person(
        self,
        session,
        user_id: int,
        text: str,
    ) -> dict | None:
        """Определяет связанного человека и возвращает его релевантные факты."""
        people = session.scalars(
            select(RelatedPerson)
            .where(RelatedPerson.user_id == user_id)
        ).all()

        if not people:
            return None

        relations = session.execute(
            select(Relation, RelatedPerson)
            .join(
                RelatedPerson,
                Relation.related_person_id == RelatedPerson.id,
            )
            .where(Relation.user_id == user_id)
        ).all()

        person = self._find_person_by_name(
            people=people,
            text=text,
        )

        relation = None

        if person is None:
            relation = self._find_relation_in_text(
                relations=relations,
                text=text,
            )

            if relation is not None:
                person = relation[1]

        if person is None:
            return None

        person_facts = session.scalars(
            select(PersonFact)
            .where(
                PersonFact.related_person_id == person.id,
                PersonFact.expires_at.is_(None),
            )
            .order_by(PersonFact.updated_at.desc())
        ).all()

        if not self._contains_any(
            text,
            self.PERSON_FACT_KEYWORDS,
        ):
            person_facts = []

        relation_type = None

        for current_relation, related_person in relations:
            if related_person.id == person.id:
                relation_type = current_relation.relation_type
                break

        return {
            "name": person.name,
            "preferred_name": person.preferred_name,
            "relation": relation_type,
            "facts": [
                self._serialize_person_fact(fact)
                for fact in person_facts
            ],
        }

    def _find_person_by_name(
        self,
        people: list[RelatedPerson],
        text: str,
    ) -> RelatedPerson | None:
        """Ищет связанного человека по имени или предпочитаемому имени."""
        for person in people:
            names = {
                person.name.lower(),
            }

            if person.preferred_name:
                names.add(
                    person.preferred_name.lower()
                )

            for name in names:
                if name and name in text:
                    return person

        return None

    def _find_relation_in_text(
        self,
        relations: list[tuple[Relation, RelatedPerson]],
        text: str,
    ) -> tuple[Relation, RelatedPerson] | None:
        """Ищет связанную персону по типу отношения в сообщении."""
        for relation, person in relations:
            relation_type = relation.relation_type.lower()

            for keyword, mapped_relation in self.RELATION_KEYWORDS.items():
                if keyword in text and (
                    relation_type == mapped_relation
                    or relation_type == keyword
                ):
                    return relation, person

        return None

    def _get_relevant_relations(
        self,
        session,
        user_id: int,
        text: str,
    ) -> list[dict]:
        """Возвращает отношения, если запрос касается связанных людей."""
        if not self._contains_relation_reference(
            text
        ):
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

    def _contains_relation_reference(
        self,
        text: str,
    ) -> bool:
        """Проверяет, содержит ли запрос упоминание связанного человека."""
        if self._contains_any(
            text,
            set(self.RELATION_KEYWORDS),
        ):
            return True

        return any(
            keyword in text
            for keyword in {
                "моя",
                "мой",
                "мою",
                "моего",
                "моей",
            }
        )

    @staticmethod
    def _serialize_user_fact(
        fact: UserFact,
    ) -> dict:
        """Преобразует UserFact в словарь."""
        return {
            "category": fact.category,
            "key": fact.key,
            "value": fact.value,
            "confidence": fact.confidence,
        }

    @staticmethod
    def _serialize_person_fact(
        fact: PersonFact,
    ) -> dict:
        """Преобразует PersonFact в словарь."""
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