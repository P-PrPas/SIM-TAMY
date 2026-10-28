"""Learning paths (Blueprint §05): stage -> objective -> knowledge units and stories.

Content lives in `content/curriculum/paths.yaml`; the loader checks every reference.
"""

from typing import Literal

from pydantic import Field, model_validator

from app.domain.case import Model, NonBlank

Dimension = Literal["discovery", "decision", "communication", "evidence_scope"]
OBJECTIVE_ID = r"^OBJ-[1-4]-\d{2}$"


class LearningObjective(Model):
    id: str = Field(pattern=OBJECTIVE_ID)
    title_th: NonBlank
    dimension: Dimension
    unit_ids: list[str] = Field(min_length=1)  # knowledge units that teach it
    story_ids: list[str] = []  # family stories or cases that practise it


class LearningStage(Model):
    stage: int = Field(ge=1, le=4)
    title_th: NonBlank
    summary_th: NonBlank
    objectives: list[LearningObjective] = Field(min_length=1)

    @model_validator(mode="after")
    def objectives_belong_to_stage(self) -> "LearningStage":
        for o in self.objectives:
            if o.id.split("-")[1] != str(self.stage):
                raise ValueError(f"{o.id} does not belong to stage {self.stage}")
        return self


class LearningPaths(Model):
    stages: list[LearningStage] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_ids(self) -> "LearningPaths":
        stages = [s.stage for s in self.stages]
        objectives = [o.id for s in self.stages for o in s.objectives]
        if len(set(stages)) != len(stages) or len(set(objectives)) != len(objectives):
            raise ValueError("duplicate stage or objective ID")
        return self

    def objective_ids(self) -> set[str]:
        return {o.id for s in self.stages for o in s.objectives}
