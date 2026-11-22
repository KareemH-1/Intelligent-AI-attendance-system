
from datetime import date

import pyodbc
from fastapi import APIRouter, HTTPException, status

from database import get_connection
from semesters.schemas import (
    SemesterCreate,
    SemesterUpdate,
    SemesterResponse,
    SemesterActivationRequest,
    SemesterActivationResponse
)

router = APIRouter(
    prefix="/api/semesters",
    tags=["Semesters"]
)


def semester_from_row(row):
    return {
        "semester_id": row[0],
        "semester_name": row[1],
        "start_date": row[2],
        "end_date": row[3],
        "is_active": bool(row[4])
    }


@router.get("", response_model=list[SemesterResponse])
def get_semesters():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT semester_id, semester_name,
                   start_date, end_date, is_active
            FROM Semesters
            ORDER BY start_date DESC
        """)

        rows = cursor.fetchall()

        return [semester_from_row(row) for row in rows]

    finally:
        connection.close()


@router.get("/{semester_id}", response_model=SemesterResponse)
def get_semester(semester_id: int):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT semester_id, semester_name,
                   start_date, end_date, is_active
            FROM Semesters
            WHERE semester_id = ?
        """, semester_id)

        row = cursor.fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Semester not found."
            )

        return semester_from_row(row)

    finally:
        connection.close()


@router.post(
    "",
    response_model=SemesterResponse,
    status_code=status.HTTP_201_CREATED
)
def create_semester(semester: SemesterCreate):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO Semesters
                (semester_name, start_date, end_date)
            OUTPUT
                INSERTED.semester_id,
                INSERTED.semester_name,
                INSERTED.start_date,
                INSERTED.end_date,
                INSERTED.is_active
            VALUES (?, ?, ?)
        """,
            semester.semester_name.strip(),
            semester.start_date,
            semester.end_date
        )

        row = cursor.fetchone()

        copied_count = 0
        if semester.copy_course_offerings:
            cursor.execute("""
                SELECT TOP 1 semester_id
                FROM Semesters
                WHERE semester_id <> ?
                ORDER BY start_date DESC, semester_id DESC
            """, row[0])
            previous = cursor.fetchone()

            if previous is not None:
                cursor.execute("""
                    INSERT INTO CourseOfferings
                        (course_id, semester_id, section_code)
                    SELECT DISTINCT
                        source.course_id,
                        ?,
                        'A'
                    FROM CourseOfferings source
                    WHERE source.semester_id = ?
                      AND NOT EXISTS (
                          SELECT 1
                          FROM CourseOfferings existing
                          WHERE existing.course_id = source.course_id
                            AND existing.semester_id = ?
                      )
                """,
                    row[0],
                    previous[0],
                    row[0],
                )
                cursor.execute("SELECT @@ROWCOUNT")
                copied_count = cursor.fetchone()[0]

        connection.commit()

        response = semester_from_row(row)
        response["copy_course_offerings"] = semester.copy_course_offerings
        response["copied_offerings_count"] = copied_count
        return response

    except pyodbc.IntegrityError:
        connection.rollback()

        raise HTTPException(
            status_code=409,
            detail="The semester could not be created because of a conflict with data"
        )

    finally:
        connection.close()


@router.put("/{semester_id}", response_model=SemesterResponse)
def update_semester(
    semester_id: int,
    semester: SemesterUpdate
):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            UPDATE Semesters
            SET semester_name = ?,
                start_date = ?,
                end_date = ?
            OUTPUT
                INSERTED.semester_id,
                INSERTED.semester_name,
                INSERTED.start_date,
                INSERTED.end_date,
                INSERTED.is_active
            WHERE semester_id = ?
        """,
            semester.semester_name.strip(),
            semester.start_date,
            semester.end_date,
            semester_id
        )

        row = cursor.fetchone()

        if row is None:
            connection.rollback()

            raise HTTPException(
                status_code=404,
                detail="Semester not found."
            )

        connection.commit()

        return semester_from_row(row)

    except pyodbc.IntegrityError:
        connection.rollback()

        raise HTTPException(
            status_code=400,
            detail="Invalid semester data."
        )

    finally:
        connection.close()


@router.patch("/{semester_id}/activate",
              response_model=SemesterActivationResponse)
def activate_semester(
    semester_id: int,
    request: SemesterActivationRequest = SemesterActivationRequest()
):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT semester_id, semester_name, end_date
            FROM Semesters WITH (UPDLOCK, HOLDLOCK)
            WHERE is_active = 1
        """)

        current = cursor.fetchone()

        # check if the semester exists
        cursor.execute("""
            SELECT semester_id, semester_name
            FROM Semesters WITH (UPDLOCK, HOLDLOCK)
            WHERE semester_id = ?
        """, semester_id)

        selected = cursor.fetchone()

        if selected is None:
            connection.rollback()

            raise HTTPException(
                status_code=404,
                detail="Semester not found."
            )

        if current is not None and current[0] == semester_id:
            connection.rollback()

            return SemesterActivationResponse(
                status="already_active",
                message="This semester is already active.",
                semester_id=selected[0],
                semester_name=selected[1]
            )

        # An active semester that has not ended requires confirmation.
        if (
            current is not None
            and current[2] >= date.today()
            and not request.confirm
        ):
            connection.rollback()

            return SemesterActivationResponse(
                status="confirmation_required",
                message=(
                    f"{current[1]} has not ended yet. "
                    f"Activating {selected[1]} will deactivate it. "
                    "Please confirm to continue."
                ),
                previous_semester_id=current[0],
                previous_semester_name=current[1],
                semester_id=selected[0],
                semester_name=selected[1],
                confirmation_required=True
            )

        if current is not None:
            cursor.execute("""
                UPDATE Semesters
                SET is_active = 0
                WHERE semester_id = ?
            """, current[0])

        cursor.execute("""
            UPDATE Semesters
            SET is_active = 1
            WHERE semester_id = ?
        """, semester_id)

        connection.commit()

        return SemesterActivationResponse(
            status="activated",
            message=f"{selected[1]} is now the active semester.",
            previous_semester_id=current[0] if current else None,
            previous_semester_name=current[1] if current else None,
            semester_id=selected[0],
            semester_name=selected[1]
        )

    except HTTPException:
        raise

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


@router.patch("/{semester_id}/deactivate")
def deactivate_semester(semester_id: int):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            UPDATE Semesters
            SET is_active = 0
            WHERE semester_id = ?
        """, semester_id)

        if cursor.rowcount == 0:
            connection.rollback()

            raise HTTPException(
                status_code=404,
                detail="Semester not found."
            )

        connection.commit()

        return {
            "status": "deactivated",
            "message": "Semester deactivated successfully."
        }

    finally:
        connection.close()
