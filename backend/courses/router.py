
import pyodbc

from fastapi import APIRouter, HTTPException, Query

from database import get_connection
from courses.schemas import (
    CourseCreate,
    CourseUpdate,
    CourseOfferingCreate,
    CourseOfferingUpdate,
)


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


@router.get("/offerings")
def get_course_offerings(
    semester_id: int = Query(gt=0),
    search: str = Query(default="", max_length=150),
):
    connection = get_connection()

    try:
        cursor = connection.cursor()
        search = search.strip()

        cursor.execute(
            """
            SELECT
                co.offering_id,
                co.course_id,
                co.semester_id,
                co.section_code,
                c.course_code,
                c.course_name,
                c.credit_hours
            FROM CourseOfferings co
            INNER JOIN Courses c ON c.course_id = co.course_id
            WHERE co.semester_id = ?
              AND (
                    ? = ''
                    OR c.course_code LIKE ?
                    OR c.course_name LIKE ?
                    OR co.section_code LIKE ?
                  )
            ORDER BY c.course_code, co.section_code
            """,
            semester_id,
            search,
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
        )

        return [
            {
                "offering_id": row.offering_id,
                "course_id": row.course_id,
                "semester_id": row.semester_id,
                "section_code": row.section_code,
                "course_code": row.course_code,
                "course_name": row.course_name,
                "credit_hours": row.credit_hours,
            }
            for row in cursor.fetchall()
        ]

    finally:
        connection.close()


@router.get("/search-options")
def search_course_options(
    search: str = Query(default="", max_length=150),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    semester_id: int | None = Query(default=None),
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
                (
                    ? = ''
                    OR course_code LIKE ?
                    OR course_name LIKE ?
                )
                AND (
                    ? IS NULL
                    OR NOT EXISTS (
                        SELECT 1
                        FROM CourseOfferings co
                        WHERE co.course_id = Courses.course_id
                          AND co.semester_id = ?
                    )
                )
            ORDER BY course_code
            OFFSET ? ROWS
            FETCH NEXT ? ROWS ONLY
            """,
            search,
            f"%{search}%",
            f"%{search}%",
            semester_id,
            semester_id,
            offset,
            limit,
        )

        rows = cursor.fetchall()

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM Courses
            WHERE
                (
                    ? = ''
                    OR course_code LIKE ?
                    OR course_name LIKE ?
                )
                AND (
                    ? IS NULL
                    OR NOT EXISTS (
                        SELECT 1
                        FROM CourseOfferings co
                        WHERE co.course_id = Courses.course_id
                          AND co.semester_id = ?
                    )
                )
            """,
            search,
            f"%{search}%",
            f"%{search}%",
            semester_id,
            semester_id,
        )

        total = cursor.fetchone()[0]

        return {
            "items": [
                {
                    "course_id": row.course_id,
                    "course_code": row.course_code,
                    "course_name": row.course_name,
                    "credit_hours": row.credit_hours,
                }
                for row in rows
            ],
            "total": total,
            "has_more": offset + len(rows) < total,
        }

    finally:
        connection.close()


@router.post("/offerings", status_code=201)
def create_course_offering(offering: CourseOfferingCreate):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT 1
            FROM CourseOfferings
            WHERE course_id = ?
              AND semester_id = ?
            """,
            offering.course_id,
            offering.semester_id,
        )

        if cursor.fetchone() is not None:
            raise HTTPException(
                status_code=409,
                detail="This course is already offered in the selected semester.",
            )

        cursor.execute(
            """
            INSERT INTO CourseOfferings (
                course_id,
                semester_id,
                section_code
            )
            OUTPUT INSERTED.offering_id
            VALUES (?, ?, ?)
            """,
            offering.course_id,
            offering.semester_id,
            "A",
        )

        offering_id = cursor.fetchone()[0]
        connection.commit()

        return {
            "message": "Course offering created successfully.",
            "offering_id": offering_id,
        }

    except HTTPException:
        connection.rollback()
        raise

    except pyodbc.IntegrityError as error:
        connection.rollback()
        message = str(error)

        if "UQ_CourseOfferings" in message or "2627" in message or "2601" in message:
            raise HTTPException(
                status_code=409,
                detail="This course section is already offered in the selected semester.",
            )

        raise HTTPException(
            status_code=400,
            detail="Unable to create the course offering.",
        )

    finally:
        connection.close()


@router.put("/offerings/{offering_id}")
def update_course_offering(
    offering_id: int,
    offering: CourseOfferingUpdate,
):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE CourseOfferings
            SET section_code = ?
            WHERE offering_id = ?
            """,
            offering.section_code.strip(),
            offering_id,
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Course offering not found.",
            )

        connection.commit()
        return {"message": "Course offering updated successfully."}

    except pyodbc.IntegrityError:
        connection.rollback()
        raise HTTPException(
            status_code=409,
            detail="This section already exists for the course in this semester.",
        )

    except HTTPException:
        connection.rollback()
        raise

    finally:
        connection.close()


@router.delete("/offerings/{offering_id}")
def delete_course_offering(offering_id: int):
    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            DELETE FROM CourseOfferings
            WHERE offering_id = ?
            """,
            offering_id,
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Course offering not found.",
            )

        connection.commit()
        return {"message": "Course offering removed successfully."}

    except pyodbc.IntegrityError:
        connection.rollback()
        raise HTTPException(
            status_code=409,
            detail="This course offering is still linked to enrollments, timetable slots, or instructor assignments.",
        )

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
