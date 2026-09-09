from typing import Literal, Optional

from pydantic import BaseModel, Field


MemoryAction = Literal[
    "remember",
    "forget",
    "ignore",
]


class MemoryDecision(BaseModel):
    """
    Решение LLM относительно долговременной памяти.

    LLM только формирует это решение.
    Реальное изменение базы выполняет MemoryManager.
    """

    action: MemoryAction

    category: Optional[str] = None

    key: Optional[str] = None

    value: Optional[str] = None

    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
    )

    reason: Optional[str] = None