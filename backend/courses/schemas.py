from pydantic import BaseModel, Field


class CourseCreate(BaseModel):
    course_code: str = Field(min_length=1, max_length=20)
    course_name: str = Field(min_length=1, max_length=150)
    credit_hours: int = Field(ge=1, le=255)


class CourseUpdate(BaseModel):
    course_code: str = Field(min_length=1, max_length=20)
    course_name: str = Field(min_length=1, max_length=150)
    credit_hours: int = Field(ge=1, le=255)


class CourseOfferingCreate(BaseModel):
    course_id: int = Field(gt=0)
    semester_id: int = Field(gt=0)


class CourseOfferingUpdate(BaseModel):
    section_code: str = Field(min_length=1, max_length=20)