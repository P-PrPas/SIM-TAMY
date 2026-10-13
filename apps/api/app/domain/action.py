"""Action catalogue (PRD 7.2)."""

from typing import Literal, Self

from pydantic import model_validator

from app.domain.case import Model

Category = Literal["HX", "DEC", "COM", "DOC"]


class Action(Model):
    id: str
    category: Category
    type: Literal["info", "critical_info", "decision", "communication", "record"]
    label_th: str
    description_th: str = ""
    examples_th: list[str]
    keywords_th: list[str] = []
    source: str | None = None  # required for critical_info under --strict

    @model_validator(mode="after")
    def _critical_needs_examples(self) -> Self:
        if self.type == "critical_info" and len(self.examples_th) < 5:
            raise ValueError("critical_info actions need at least 5 examples_th")
        return self
