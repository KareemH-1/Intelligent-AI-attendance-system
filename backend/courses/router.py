
import pyodbc

from fastapi import APIRouter, HTTPException, Query

from database import get_connection
from courses.schemas import CourseCreate, CourseUpdate


router = APIRouter(
    prefix="/api/courses",
    tags=["Courses"]
)


@router.get("")
def get_courses(
    search: str = Query(default="")
):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        search = search.strip()

        cursor.execute(
            """
            SELECT
                course_id,
                course_code,
                course_name,
                credit_hours
            FROM Courses
            WHERE
                course_code LIKE ?
                OR course_name LIKE ?
            ORDER BY course_code
            """,
            f"%{search}%",
            f"%{search}%"
        )

        rows = cursor.fetchall()

        courses = []

        for row in rows:
            courses.append({
                "course_id": row.course_id,
                "course_code": row.course_code,
                "course_name": row.course_name,
                "credit_hours": row.credit_hours
            })

        return courses

    finally:
        connection.close()


@router.get("/{course_id}")
def get_course(course_id: int):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                course_id,
                course_code,
                course_name,
                credit_hours
            FROM Courses
            WHERE course_id = ?
            """,
            course_id
        )

        row = cursor.fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Course not found."
            )

        return {
            "course_id": row.course_id,
            "course_code": row.course_code,
            "course_name": row.course_name,
            "credit_hours": row.credit_hours
        }

    finally:
        connection.close()


@router.post("", status_code=201)
def create_course(course: CourseCreate):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        course_code = course.course_code.strip()
        course_name = course.course_name.strip()

        if not course_code or not course_name:
            raise HTTPException(
                status_code=422,
                detail="Course code and name cannot be empty."
            )

        cursor.execute(
            """
            INSERT INTO Courses (
                course_code,
                course_name,
                credit_hours
            )
            OUTPUT INSERTED.course_id
            VALUES (?, ?, ?)
            """,
            course_code,
            course_name,
            course.credit_hours
        )

        course_id = cursor.fetchone()[0]

        connection.commit()

        return {
            "message": "Course created successfully.",
            "course_id": course_id
        }

    except pyodbc.IntegrityError:
        connection.rollback()

        raise HTTPException(
            status_code=409,
            detail="A course with this course code already exists."
        )

    finally:
        connection.close()


@router.put("/{course_id}")
def update_course(
    course_id: int,
    course: CourseUpdate
):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        course_code = course.course_code.strip()
        course_name = course.course_name.strip()

        if not course_code or not course_name:
            raise HTTPException(
                status_code=422,
                detail="Course code and name cannot be empty."
            )

        cursor.execute(
            """
            UPDATE Courses
            SET
                course_code = ?,
                course_name = ?,
                credit_hours = ?
            WHERE course_id = ?
            """,
            course_code,
            course_name,
            course.credit_hours,
            course_id
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Course not found."
            )

        connection.commit()

        return {
            "message": "Course updated successfully."
        }

    except pyodbc.IntegrityError:
        connection.rollback()

        raise HTTPException(
            status_code=409,
            detail="A course with this course code already exists."
        )

    finally:
        connection.close()


@router.delete("/{course_id}")
def delete_course(course_id: int):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM Courses
            WHERE course_id = ?
            """,
            course_id
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Course not found."
            )

        connection.commit()

        return {
            "message": "Course deleted successfully."
        }

    except pyodbc.IntegrityError:
        connection.rollback()

        raise HTTPException(
            status_code=409,
            detail=(
                "This course cannot be deleted because it is already associated with course offerings."
            )
        )

    finally:
        connection.close()
