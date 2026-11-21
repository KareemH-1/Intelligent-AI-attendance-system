
from datetime import date
from pydantic import BaseModel, Field, model_validator


class SemesterCreate(BaseModel):
    semester_name: str = Field(min_length=1, max_length=50)
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("The semster end_date cant be before the start_date")

        return self


class SemesterUpdate(BaseModel):
    semester_name: str = Field(min_length=1, max_length=50)
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("The semster end_date cant be before the start_date.")

        return self


class SemesterResponse(BaseModel):
    semester_id: int
    semester_name: str
    start_date: date
    end_date: date
    is_active: bool



class SemesterActivationRequest(BaseModel):
    confirm: bool = False


class SemesterActivationResponse(BaseModel):
    status: str
    message: str
    previous_semester_id: int | None = None
    previous_semester_name: str | None = None
    semester_id: int
    semester_name: str
    confirmation_required: bool = False
