
from fastapi import FastAPI, HTTPException
from database import get_connection
from fastapi.middleware.cors import CORSMiddleware

from semesters.router import router as semester_router

app = FastAPI(
    title="backend for the ai attendance system",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(semester_router)

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
