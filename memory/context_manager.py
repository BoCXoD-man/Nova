"""
Модуль: memory/context_manager.py

Формирует релевантный контекст пользователя для текущего запроса.
Определяет пользователя или связанного человека, о котором идёт речь,
и передаёт модели соответствующие факты вместе с отношением к пользователю.
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
        "женой": "wife",
        "муж": "husband",
        "мужа": "husband",
        "мужу": "husband",
        "мужем": "husband",
        "дочь": "daughter",
        "дочери": "daughter",
        "дочерью": "daughter",
        "дочка": "daughter",
        "дочку": "daughter",
        "сын": "son",
        "сына": "son",
        "сыну": "son",
        "сыном": "son",
        "мама": "mother",
        "маму": "mother",
        "маме": "mother",
        "матери": "mother",
        "мать": "mother",
        "папа": "father",
        "папу": "father",
        "папе": "father",
        "отец": "father",
        "отца": "father",
        "брата": "brother",
        "брат": "brother",
        "брату": "brother",
        "сестра": "sister",
        "сестру": "sister",
        "сестре": "sister",
        "друг": "friend",
        "друга": "friend",
        "другу": "friend",
        "друзья": "friend",
    }

    RELATION_LABELS = {
        "wife": "твоя жена",
        "husband": "твой муж",
        "daughter": "твоя дочь",
        "son": "твой сын",
        "mother": "твоя мама",
        "father": "твой отец",
        "brother": "твой брат",
        "sister": "твоя сестра",
        "friend": "твой друг",
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
        "дата рождения",
        "день рождения",
        "родился",
        "родилась",
        "рождения",
    }

    PERSON_FACT_KEYWORDS = {
        "любит",
        "люблю",
        "нравится",
        "любим",
        "любимая",
        "любимый",
        "предпочитает",
        "хочет",
        "играет",
        "работает",
        "учится",
        "возраст",
        "день рождения",
        "дата рождения",
        "рождения",
        "родился",
        "родилась",
        "еда",
        "любимая еда",
        "хобби",
        "интерес",
        "нравится",
        "когда",
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
            "birth_date": user.birth_date,
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
            .order_by(UserFact.updated_at.desc())
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
            return [
                self._serialize_user_fact(fact)
                for fact in facts
                if fact.key in {
                    "birth_date",
                }
            ]

        return []

    def _get_relevant_person(
        self,
        session,
        user_id: int,
        text: str,
    ) -> dict | None:
        """Определяет связанного человека и возвращает его факты."""
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

        relation_type = self._get_person_relation(
            relations=relations,
            person_id=person.id,
        )

        person_facts = session.scalars(
            select(PersonFact)
            .where(
                PersonFact.related_person_id == person.id,
                PersonFact.expires_at.is_(None),
            )
            .order_by(PersonFact.updated_at.desc())
        ).all()

        return {
            "name": person.name,
            "preferred_name": person.preferred_name,
            "relation": relation_type,
            "relation_label": self._get_relation_label(
                relation_type,
            ),
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
                person.name.lower().strip(),
            }

            if person.preferred_name:
                names.add(
                    person.preferred_name.lower().strip()
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
            relation_type = relation.relation_type.lower().strip()

            for keyword, mapped_relation in self.RELATION_KEYWORDS.items():
                if keyword not in text:
                    continue

                if relation_type == mapped_relation:
                    return relation, person

        return None

    def _get_person_relation(
        self,
        relations: list[tuple[Relation, RelatedPerson]],
        person_id: int,
    ) -> str | None:
        """Возвращает тип отношения пользователя к указанному человеку."""
        for relation, person in relations:
            if person.id == person_id:
                return relation.relation_type

        return None

    def _get_relation_label(
        self,
        relation_type: str | None,
    ) -> str | None:
        """Возвращает естественное обращение к человеку с позиции пользователя."""
        if relation_type is None:
            return None

        return self.RELATION_LABELS.get(
            relation_type.lower().strip(),
            relation_type,
        )

    def _get_relevant_relations(
        self,
        session,
        user_id: int,
        text: str,
    ) -> list[dict]:
        """Возвращает отношения, если запрос касается связанных людей."""
        if not self._contains_relation_reference(text):
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
            relation_type = relation.relation_type

            relations.append(
                {
                    "person": person.name,
                    "preferred_name": person.preferred_name,
                    "relation": relation_type,
                    "relation_label": self._get_relation_label(
                        relation_type,
                    ),
                    "confidence": relation.confidence,
                }
            )

        return relations

    def _contains_relation_reference(
        self,
        text: str,
    ) -> bool:
        """Проверяет, содержит ли запрос ссылку на связанного человека."""
        if self._contains_any(
            text,
            set(self.RELATION_KEYWORDS),
        ):
            return True

        return any(
            word in text
            for word in {
                "моя",
                "мой",
                "мою",
                "моего",
                "моей",
                "моими",
                "моих",
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