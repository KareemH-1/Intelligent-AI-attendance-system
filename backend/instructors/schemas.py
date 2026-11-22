from pydantic import BaseModel, Field


class InstructorCreate(BaseModel):
    university_id: str = Field(min_length=1, max_length=30)
    full_name: str = Field(min_length=1, max_length=150)
    email: str = Field(min_length=1, max_length=150)
    department: str = Field(min_length=1, max_length=100)
    instructor_type: str = Field(pattern="^(Lecturer|TA)$")
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=6, max_length=255)


class InstructorUpdate(BaseModel):
    university_id: str = Field(min_length=1, max_length=30)
    full_name: str = Field(min_length=1, max_length=150)
    email: str = Field(min_length=1, max_length=150)
    department: str = Field(min_length=1, max_length=100)
    instructor_type: str = Field(pattern="^(Lecturer|TA)$")
    username: str | None = Field(default=None, max_length=100)
    password: str | None = Field(default=None, min_length=6, max_length=255)


class InstructorAssignmentCreate(BaseModel):
    instructor_id: int = Field(gt=0)
    offering_id: int = Field(gt=0)
    instructor_role: str = Field(pattern="^(Lecturer|TA)$")


class InstructorAccountStatusUpdate(BaseModel):
    is_active: bool
