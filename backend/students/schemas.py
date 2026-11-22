
from pydantic import BaseModel, Field


class StudentCreate(BaseModel):
    university_id: str = Field(min_length=1, max_length=30)
    full_name: str = Field(min_length=1, max_length=150)
    email: str | None = Field(default=None, max_length=150)
    department: str = Field(min_length=1, max_length=100)
    academic_year: int = Field(ge=1, le=7)


class StudentUpdate(BaseModel):
    university_id: str = Field(min_length=1, max_length=30)
    full_name: str = Field(min_length=1, max_length=150)
    email: str | None = Field(default=None, max_length=150)
    department: str = Field(min_length=1, max_length=100)
    academic_year: int = Field(ge=1, le=7)


class StudentEnrollmentCreate(BaseModel):
    offering_id: int = Field(gt=0)
