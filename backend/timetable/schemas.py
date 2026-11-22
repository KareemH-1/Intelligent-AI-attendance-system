from datetime import time
from pydantic import BaseModel, Field, model_validator


class TimetableSlotCreate(BaseModel):
    semester_id: int = Field(gt=0)
    offering_id: int = Field(gt=0)
    hall_id: int = Field(gt=0)
    primary_instructor_id: int = Field(gt=0)
    ta_instructor_id: int | None = None
    day_of_week: int = Field(ge=1, le=7)
    start_time: time
    end_time: time

    @model_validator(mode="after")
    def validate_times(self):
        if self.end_time <= self.start_time:
            raise ValueError("End time must be after start time.")
        if self.ta_instructor_id == self.primary_instructor_id:
            raise ValueError("The TA must be different from the lecturer.")
        if self.ta_instructor_id is not None:
            raise ValueError("Choose either a lecturer or a TA for the hall.")
        return self


class TimetableSlotUpdate(BaseModel):
    offering_id: int = Field(gt=0)
    primary_instructor_id: int = Field(gt=0)
    ta_instructor_id: int | None = None
    day_of_week: int = Field(ge=1, le=7)
    start_time: time
    end_time: time

    @model_validator(mode="after")
    def validate_times(self):
        if self.end_time <= self.start_time:
            raise ValueError("End time must be after start time.")
        if self.ta_instructor_id == self.primary_instructor_id:
            raise ValueError("The TA must be different from the lecturer.")
        if self.ta_instructor_id is not None:
            raise ValueError("Choose either a lecturer or a TA for the hall.")
        return self
