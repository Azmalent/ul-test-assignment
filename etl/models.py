"""Pydantic-модели для валидации данных."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Window(BaseModel):
    """Окно обработки по loading_date: [start_date, end_date)."""

    model_config = ConfigDict(frozen=True)

    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_order(self) -> "Window":
        if self.start_date >= self.end_date:
            raise ValueError("start_date должен быть меньше end_date")
        return self


class LoadResult(BaseModel):
    """Результат загрузки staging в core и карантин."""

    model_config = ConfigDict(frozen=True)

    run_id: UUID
    valid_rows: int = Field(ge=0)
    quarantined_rows: int = Field(ge=0)
    core_deleted: int = Field(ge=0)
    quarantine_deleted: int = Field(ge=0)
