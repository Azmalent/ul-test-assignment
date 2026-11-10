"""Pydantic-модели для валидации данных."""

from datetime import date, datetime

import pendulum
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def to_pendulum_date(
    value: pendulum.Date | pendulum.DateTime | date | datetime | str,
) -> pendulum.Date:
    """Приводит значение к pendulum.Date."""
    if isinstance(value, pendulum.DateTime):
        return value.date()
    if isinstance(value, datetime):
        return pendulum.instance(value).date()
    if isinstance(value, pendulum.Date):
        return value
    if isinstance(value, date):
        return pendulum.date(value.year, value.month, value.day)
    return pendulum.parse(str(value)).date()


class Window(BaseModel):
    """Окно обработки по loading_date: [start_date, end_date)."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    start_date: pendulum.Date
    end_date: pendulum.Date

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def parse_date(
        cls,
        value: pendulum.Date | pendulum.DateTime | date | datetime | str,
    ) -> pendulum.Date:
        return to_pendulum_date(value)

    @model_validator(mode="after")
    def validate_order(self) -> "Window":
        if self.start_date >= self.end_date:
            raise ValueError("start_date должен быть меньше end_date")
        return self


class LoadResult(BaseModel):
    """Результат загрузки staging в core и карантин."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    valid_rows: int = Field(ge=0)
    quarantined_rows: int = Field(ge=0)
    core_deleted: int = Field(ge=0)
    quarantine_deleted: int = Field(ge=0)
