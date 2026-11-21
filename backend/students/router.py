
from fastapi import APIRouter, HTTPException, Query
import pyodbc

from database import get_connection
from students.schemas import StudentCreate, StudentUpdate


router = APIRouter(
    prefix="/students",
    tags=["Students"]
)


def row_to_student(row):
    return {
        "student_id": row[0],
        "person_id": row[1],
        "university_id": row[2],
        "full_name": row[3],
        "email": row[4],
        "department": row[5],
        "academic_year": row[6]
    }


def is_unique_violation(error):
    message = str(error)
    return "2627" in message or "2601" in message


def get_student_query():
    return """
        SELECT
            s.student_id,
            p.person_id,
            p.university_id,
            p.full_name,
            p.email,
            s.department,
            s.academic_year
        FROM Students s
        INNER JOIN People p
            ON s.person_id = p.person_id
    """


@router.get("")
def get_students(
    search: str = Query(default="", max_length=150)
):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        query = get_student_query()

        if search.strip():
            query += """
                WHERE
                    p.university_id LIKE ?
                    OR p.full_name LIKE ?
                    OR p.email LIKE ?
                    OR s.department LIKE ?
            """

            search_value = f"%{search.strip()}%"

            cursor.execute(
                query + " ORDER BY p.full_name",
                search_value,
                search_value,
                search_value,
                search_value
            )
        else:
            cursor.execute(query + " ORDER BY p.full_name")

        rows = cursor.fetchall()

        return [row_to_student(row) for row in rows]

    finally:
        connection.close()


@router.get("/next-university-id")
def get_next_university_id():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                CASE
                    WHEN NOT EXISTS (
                        SELECT 1 FROM People
                    )
                    THEN CONVERT(BIGINT, IDENT_SEED('dbo.People'))
                    ELSE CONVERT(
                        BIGINT,
                        IDENT_CURRENT('dbo.People')
                        + IDENT_INCR('dbo.People')
                    )
                END
        """)

        next_id = cursor.fetchone()[0]

        return {
            "university_id": str(next_id)
        }

    finally:
        connection.close()
        
@router.get("/{student_id}")
def get_student(student_id: int):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        query = get_student_query() + """
            WHERE s.student_id = ?
        """

        cursor.execute(query, student_id)

        row = cursor.fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Student not found."
            )

        return row_to_student(row)

    finally:
        connection.close()


@router.post("", status_code=201)
def create_student(student: StudentCreate):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO People
                (university_id, full_name, email)
            OUTPUT INSERTED.person_id
            VALUES (?, ?, ?)
        """,
            student.university_id.strip(),
            student.full_name.strip(),
            student.email.strip() if student.email else None
        )

        person_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO Students
                (person_id, department, academic_year)
            OUTPUT INSERTED.student_id
            VALUES (?, ?, ?)
        """,
            person_id,
            student.department.strip(),
            student.academic_year
        )

        student_id = cursor.fetchone()[0]

        connection.commit()

        return {
            "message": "Student registered successfully.",
            "student_id": student_id,
            "person_id": person_id
        }

    except pyodbc.IntegrityError as error:
        connection.rollback()

        if is_unique_violation(error):
            raise HTTPException(
                status_code=409,
                detail="University ID or email already exists."
            )

        raise HTTPException(
            status_code=400,
            detail="Unable to register student. Please check the submitted information."
        )

    finally:
        connection.close()


@router.put("/{student_id}")
def update_student(student_id: int, student: StudentUpdate):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT person_id
            FROM Students
            WHERE student_id = ?
        """, student_id)

        row = cursor.fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Student not found."
            )

        person_id = row[0]

        cursor.execute("""
            UPDATE People
            SET
                university_id = ?,
                full_name = ?,
                email = ?
            WHERE person_id = ?
        """,
            student.university_id.strip(),
            student.full_name.strip(),
            student.email.strip() if student.email else None,
            person_id
        )

        cursor.execute("""
            UPDATE Students
            SET
                department = ?,
                academic_year = ?
            WHERE student_id = ?
        """,
            student.department.strip(),
            student.academic_year,
            student_id
        )

        connection.commit()

        return {
            "message": "Student updated successfully."
        }

    except pyodbc.IntegrityError as error:
        connection.rollback()

        if is_unique_violation(error):
            raise HTTPException(
                status_code=409,
                detail="University ID or email already exists."
            )

        raise HTTPException(
            status_code=400,
            detail="Unable to update student information."
        )

    finally:
        connection.close()


@router.delete("/{student_id}")
def delete_student(student_id: int):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT person_id
            FROM Students
            WHERE student_id = ?
        """, student_id)

        row = cursor.fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Student not found."
            )

        person_id = row[0]

        cursor.execute("""
            DELETE FROM FaceEmbeddings
            WHERE person_id = ?
        """, person_id)

        cursor.execute("""
            DELETE FROM Students
            WHERE student_id = ?
        """, student_id)

        cursor.execute("""
            DELETE FROM People
            WHERE person_id = ?
        """, person_id)

        connection.commit()

        return {
            "message": "Student and associated face embeddings deleted successfully."
        }

    except pyodbc.IntegrityError as error:
        connection.rollback()

        if "547" in str(error):
            raise HTTPException(
                status_code=409,
                detail=(
                    "This student cannot be deleted because they have "
                    "existing enrollments, attendance records, or other "
                    "linked records."
                )
            )

        raise HTTPException(
            status_code=400,
            detail="Unable to delete student."
        )

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
