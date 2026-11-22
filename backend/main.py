
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from database import get_connection
from fastapi.middleware.cors import CORSMiddleware

from semesters.router import router as semester_router
from courses.router import router as course_router
from students.router import router as student_router
from instructors.router import router as instructor_router
from halls.router import router as hall_router
from timetable.router import router as timetable_router

from vision_layer.registration_router import router as registration_router

app = FastAPI(
    title="backend for the ai attendance system",
    version="1.0.0"
)


@app.exception_handler(RequestValidationError)
async def friendly_validation_error(request: Request, error: RequestValidationError):
    friendly_messages = []
    field_names = {
        "university_id": "University ID",
        "full_name": "Full name",
        "email": "Email",
        "department": "Department",
        "instructor_type": "Instructor type",
        "username": "Username",
        "password": "Password",
        "instructor_id": "Instructor",
        "offering_id": "Course offering",
        "instructor_role": "Instructor role",
        "is_active": "Account status",
        "semester_id": "Semester",
    }

    for item in error.errors():
        field = str(item["loc"][-1]) if item["loc"] else "Field"
        label = field_names.get(field, field.replace("_", " ").title())
        error_type = item["type"]

        if field == "password" and error_type in (
            "string_too_short",
            "too_short",
        ):
            friendly_messages.append("Password must contain at least 6 characters.")
        elif error_type in ("string_too_short", "too_short"):
            friendly_messages.append(f"{label} is required.")
        elif error_type in ("string_too_long", "too_long"):
            friendly_messages.append(f"{label} is too long.")
        elif error_type == "missing":
            friendly_messages.append(f"{label} is required.")
        elif field == "email" and error_type == "value_error":
            friendly_messages.append("Enter a valid email address.")
        elif field in ("instructor_type", "instructor_role"):
            friendly_messages.append(f"{label} must be Lecturer or TA.")
        else:
            friendly_messages.append(f"Please check {label.lower()}.")

    message = " ".join(dict.fromkeys(friendly_messages))
    return JSONResponse(status_code=422, content={"detail": message})

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(semester_router)
app.include_router(course_router)
app.include_router(student_router, prefix="/api")
app.include_router(instructor_router, prefix="/api")
app.include_router(hall_router, prefix="/api")
app.include_router(timetable_router, prefix="/api")
app.include_router(registration_router, prefix="/api")


@app.get("/")
def home():
    return {
        "message": "api is running"
    }


@app.get("/health/database")
def database_health():
    try:
        connection = get_connection()

        cursor = connection.cursor()
        cursor.execute("SELECT DB_NAME()")

        database_name = cursor.fetchone()[0]

        cursor.close()
        connection.close()

        return {
            "status": "connected",
            "database": database_name
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Database connection failed: {str(error)}"
        )
