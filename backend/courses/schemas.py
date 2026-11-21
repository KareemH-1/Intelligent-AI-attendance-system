from pydantic import BaseModel, Field


class CourseCreate(BaseModel):
    course_code: str = Field(min_length=1, max_length=20)
    course_name: str = Field(min_length=1, max_length=150)
    credit_hours: int = Field(ge=1, le=255)


class CourseUpdate(BaseModel):
    course_code: str = Field(min_length=1, max_length=20)
    course_name: str = Field(min_length=1, max_length=150)
    credit_hours: int = Field(ge=1, le=255)