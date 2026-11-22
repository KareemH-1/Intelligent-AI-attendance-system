from pydantic import BaseModel, Field


class HallCreate(BaseModel):
    hall_name: str = Field(min_length=1, max_length=50)
    building: str = Field(min_length=1, max_length=100)
    capacity: int = Field(gt=0)
    terminal_password: str = Field(min_length=6, max_length=255)


class HallUpdate(BaseModel):
    hall_name: str = Field(min_length=1, max_length=50)
    building: str = Field(min_length=1, max_length=100)
    capacity: int = Field(gt=0)


class TerminalPasswordUpdate(BaseModel):
    terminal_password: str = Field(min_length=6, max_length=255)


class TerminalStatusUpdate(BaseModel):
    is_active: bool
