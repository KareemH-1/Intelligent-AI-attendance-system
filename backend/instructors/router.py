import pyodbc
from fastapi import APIRouter, HTTPException, Query

from auth.security import DEFAULT_INITIAL_PASSWORD, hash_password
from database import get_connection
from instructors.schemas import (
    InstructorCreate,
    InstructorUpdate,
    InstructorAssignmentCreate,
    InstructorAccountStatusUpdate,
)


router = APIRouter(prefix="/instructors", tags=["Instructors"])


def is_unique_violation(error):
    message = str(error)
    return "2627" in message or "2601" in message


def get_instructor_query():
    return """
        SELECT
            i.instructor_id,
            p.person_id,
            p.university_id,
            p.full_name,
            p.email,
            i.department,
            i.instructor_type,
            ua.account_id,
            ua.username,
            ua.is_active,
            CASE WHEN EXISTS (
                SELECT 1
                FROM FaceEmbeddings fe
                WHERE fe.person_id = p.person_id
                  AND fe.is_active = 1
            ) THEN CONVERT(BIT, 1)
            ELSE CONVERT(BIT, 0)
            END AS has_face_registration
        FROM Instructors i
        INNER JOIN People p ON i.person_id = p.person_id
        INNER JOIN UserAccounts ua ON ua.person_id = p.person_id
    """


def row_to_instructor(row):
    return {
        "instructor_id": row[0],
        "person_id": row[1],
        "university_id": row[2],
        "full_name": row[3],
        "email": row[4],
        "department": row[5],
        "instructor_type": row[6],
        "account_id": row[7],
        "username": row[8],
        "is_active": bool(row[9]),
        "has_face_registration": bool(row[10]),
    }


@router.get("")
def get_instructors(
    search: str = Query(default="", max_length=150),
    instructor_type: str = Query(default="", max_length=20),
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        query = get_instructor_query()
        conditions = []
        parameters = []

        if search.strip():
            conditions.append("""
                (p.university_id LIKE ?
                 OR p.full_name LIKE ?
                 OR p.email LIKE ?
                 OR i.department LIKE ?
                 OR ua.username LIKE ?)
            """)
            value = f"%{search.strip()}%"
            parameters.extend([value, value, value, value, value])

        if instructor_type:
            if instructor_type not in ("Lecturer", "TA"):
                raise HTTPException(status_code=422, detail="Invalid instructor type.")
            conditions.append("i.instructor_type = ?")
            parameters.append(instructor_type)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        cursor.execute(query + " ORDER BY p.full_name", *parameters)
        return [row_to_instructor(row) for row in cursor.fetchall()]
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
                    WHEN NOT EXISTS (SELECT 1 FROM People)
                    THEN CONVERT(BIGINT, IDENT_SEED('dbo.People'))
                    ELSE CONVERT(BIGINT,
                        IDENT_CURRENT('dbo.People') + IDENT_INCR('dbo.People'))
                END
        """)
        return {"university_id": str(cursor.fetchone()[0])}
    finally:
        connection.close()


@router.get("/{instructor_id}")
def get_instructor(instructor_id: int):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            get_instructor_query() + " WHERE i.instructor_id = ?",
            instructor_id,
        )
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Instructor not found.")
        return row_to_instructor(row)
    finally:
        connection.close()


@router.post("", status_code=201)
def create_instructor(instructor: InstructorCreate):
    connection = get_connection()
    try:
        connection.autocommit = False
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT r.role_id
            FROM Roles r
            WHERE r.role_name = ?
            """,
            instructor.instructor_type,
        )
        role = cursor.fetchone()
        if role is None:
            raise HTTPException(
                status_code=409,
                detail=f"The {instructor.instructor_type} role is not configured.",
            )

        cursor.execute(
            """
            INSERT INTO People (university_id, full_name, email)
            OUTPUT INSERTED.person_id
            VALUES (?, ?, ?)
            """,
            instructor.university_id.strip(),
            instructor.full_name.strip(),
            instructor.email.strip(),
        )
        person_id = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO Instructors (person_id, department, instructor_type)
            OUTPUT INSERTED.instructor_id
            VALUES (?, ?, ?)
            """,
            person_id,
            instructor.department.strip(),
            instructor.instructor_type,
        )
        instructor_id = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO UserAccounts
                (person_id, role_id, username, password_hash, is_active,
                 must_change_password)
            OUTPUT INSERTED.account_id
            VALUES (?, ?, ?, ?, 1, 1)
            """,
            person_id,
            role[0],
            instructor.username.strip(),
            hash_password(DEFAULT_INITIAL_PASSWORD),
        )
        account_id = cursor.fetchone()[0]

        connection.commit()
        return {
            "message": "Instructor registered successfully.",
            "instructor_id": instructor_id,
            "person_id": person_id,
            "account_id": account_id,
        }
    except HTTPException:
        connection.rollback()
        raise
    except pyodbc.IntegrityError as error:
        connection.rollback()
        if is_unique_violation(error):
            raise HTTPException(
                status_code=409,
                detail="University ID, email, or username already exists.",
            )
        raise HTTPException(
            status_code=400,
            detail="Unable to register instructor. Check the submitted information.",
        )
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


@router.put("/{instructor_id}")
def update_instructor(instructor_id: int, instructor: InstructorUpdate):
    connection = get_connection()
    try:
        connection.autocommit = False
        cursor = connection.cursor()

        cursor.execute("""
            SELECT i.person_id
            FROM Instructors i
            WHERE i.instructor_id = ?
        """, instructor_id)
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Instructor not found.")
        person_id = row[0]

        cursor.execute("""
            SELECT role_id
            FROM Roles
            WHERE role_name = ?
        """, instructor.instructor_type)
        role = cursor.fetchone()
        if role is None:
            raise HTTPException(
                status_code=409,
                detail=f"The {instructor.instructor_type} role is not configured.",
            )

        cursor.execute("""
            SELECT TOP 1 1
            FROM InstructorOfferings io
            INNER JOIN CourseOfferings co ON co.offering_id = io.offering_id
            WHERE io.instructor_id = ?
              AND io.instructor_role <> ?
        """, instructor_id, instructor.instructor_type)
        if cursor.fetchone() is not None:
            raise HTTPException(
                status_code=409,
                detail="Remove incompatible course assignments before changing instructor type.",
            )

        cursor.execute("""
            UPDATE People
            SET university_id = ?, full_name = ?, email = ?
            WHERE person_id = ?
        """,
            instructor.university_id.strip(),
            instructor.full_name.strip(),
            instructor.email.strip(),
            person_id,
        )
        cursor.execute("""
            UPDATE Instructors
            SET department = ?, instructor_type = ?
            WHERE instructor_id = ?
        """,
            instructor.department.strip(),
            instructor.instructor_type,
            instructor_id,
        )
        cursor.execute("""
            UPDATE UserAccounts
            SET role_id = ?
            WHERE person_id = ?
        """, role[0], person_id)

        if instructor.username is not None:
            cursor.execute("""
                UPDATE UserAccounts
                SET username = ?
                WHERE person_id = ?
            """, instructor.username.strip(), person_id)

        if instructor.password is not None:
            cursor.execute("""
                UPDATE UserAccounts
                SET password_hash = ?, must_change_password = 1
                WHERE person_id = ?
            """, hash_password(instructor.password), person_id)

        connection.commit()
        return {"message": "Instructor updated successfully."}
    except HTTPException:
        connection.rollback()
        raise
    except pyodbc.IntegrityError as error:
        connection.rollback()
        if is_unique_violation(error):
            raise HTTPException(
                status_code=409,
                detail="University ID, email, or username already exists.",
            )
        raise HTTPException(status_code=400, detail="Unable to update instructor.")
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


@router.patch("/{instructor_id}/account-status")
def update_instructor_account_status(
    instructor_id: int,
    request: InstructorAccountStatusUpdate,
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE ua
            SET ua.is_active = ?
            FROM UserAccounts ua
            INNER JOIN Instructors i ON i.person_id = ua.person_id
            WHERE i.instructor_id = ?
        """, 1 if request.is_active else 0, instructor_id)

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Instructor not found.")

        connection.commit()
        return {
            "message": (
                "Instructor account activated successfully."
                if request.is_active
                else "Instructor account deactivated successfully."
            ),
            "is_active": request.is_active,
        }
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@router.get("/offerings/semesters/{semester_id}")
def get_semester_offerings(
    semester_id: int,
    instructor_id: int | None = Query(default=None),
    search: str = Query(default="", max_length=150),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        search = search.strip()
        cursor.execute("""
            SELECT
                co.offering_id,
                co.course_id,
                c.course_code,
                c.course_name,
                co.section_code
            FROM CourseOfferings co
            INNER JOIN Courses c ON c.course_id = co.course_id
            WHERE co.semester_id = ?
              AND (
                    ? = ''
                    OR c.course_code LIKE ?
                    OR c.course_name LIKE ?
                    OR co.section_code LIKE ?
                  )
              AND (
                    ? IS NULL
                    OR NOT EXISTS (
                        SELECT 1
                        FROM InstructorOfferings io
                        WHERE io.offering_id = co.offering_id
                          AND io.instructor_id = ?
                    )
                  )
            ORDER BY c.course_code, co.section_code
            OFFSET ? ROWS
            FETCH NEXT ? ROWS ONLY
        """,
            semester_id,
            search,
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            instructor_id,
            instructor_id,
            offset,
            limit,
        )

        items = [
            {
                "offering_id": row[0],
                "course_id": row[1],
                "course_code": row[2],
                "course_name": row[3],
                "section_code": row[4],
            }
            for row in cursor.fetchall()
        ]

        cursor.execute("""
            SELECT COUNT(*)
            FROM CourseOfferings co
            INNER JOIN Courses c ON c.course_id = co.course_id
            WHERE co.semester_id = ?
              AND (
                    ? = ''
                    OR c.course_code LIKE ?
                    OR c.course_name LIKE ?
                    OR co.section_code LIKE ?
                  )
              AND (
                    ? IS NULL
                    OR NOT EXISTS (
                        SELECT 1
                        FROM InstructorOfferings io
                        WHERE io.offering_id = co.offering_id
                          AND io.instructor_id = ?
                    )
                  )
        """,
            semester_id,
            search,
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            instructor_id,
            instructor_id,
        )
        total = cursor.fetchone()[0]

        return {
            "items": items,
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": offset + len(items) < total,
        }
    finally:
        connection.close()


@router.get("/{instructor_id}/offerings")
def get_instructor_offerings(
    instructor_id: int,
    semester_id: int = Query(gt=0),
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT
                io.instructor_offering_id,
                io.offering_id,
                io.instructor_role,
                c.course_code,
                c.course_name,
                co.section_code
            FROM InstructorOfferings io
            INNER JOIN CourseOfferings co ON co.offering_id = io.offering_id
            INNER JOIN Courses c ON c.course_id = co.course_id
            INNER JOIN Instructors i ON i.instructor_id = io.instructor_id
            WHERE io.instructor_id = ?
              AND co.semester_id = ?
            ORDER BY c.course_code, co.section_code
        """, instructor_id, semester_id)

        return [
            {
                "instructor_offering_id": row[0],
                "offering_id": row[1],
                "instructor_role": row[2],
                "course_code": row[3],
                "course_name": row[4],
                "section_code": row[5],
            }
            for row in cursor.fetchall()
        ]
    finally:
        connection.close()


@router.post("/offerings", status_code=201)
def create_instructor_offering(assignment: InstructorAssignmentCreate):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT i.instructor_type
            FROM Instructors i
            WHERE i.instructor_id = ?
        """, assignment.instructor_id)
        instructor = cursor.fetchone()
        if instructor is None:
            raise HTTPException(status_code=404, detail="Instructor not found.")
        if instructor[0] != assignment.instructor_role:
            raise HTTPException(
                status_code=400,
                detail=f"{instructor[0]} instructors can only be assigned as {instructor[0]}.",
            )

        cursor.execute("""
            SELECT offering_id
            FROM CourseOfferings
            WHERE offering_id = ?
        """, assignment.offering_id)
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Course offering not found.")

        cursor.execute(
            """
            INSERT INTO InstructorOfferings
                (instructor_id, offering_id, instructor_role)
            OUTPUT INSERTED.instructor_offering_id
            VALUES (?, ?, ?)
            """,
            assignment.instructor_id,
            assignment.offering_id,
            assignment.instructor_role,
        )
        assignment_id = cursor.fetchone()[0]
        connection.commit()
        return {
            "message": "Instructor assigned successfully.",
            "instructor_offering_id": assignment_id,
        }
    except HTTPException:
        connection.rollback()
        raise
    except pyodbc.IntegrityError:
        connection.rollback()
        raise HTTPException(
            status_code=409,
            detail="This instructor is already assigned to the course offering.",
        )
    finally:
        connection.close()


@router.delete("/offerings/{assignment_id}")
def delete_instructor_offering(assignment_id: int):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            DELETE FROM InstructorOfferings
            WHERE instructor_offering_id = ?
        """, assignment_id)
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Assignment not found.")
        connection.commit()
        return {"message": "Instructor assignment removed successfully."}
    finally:
        connection.close()
