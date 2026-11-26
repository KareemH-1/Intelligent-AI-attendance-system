from datetime import time

import pyodbc
from fastapi import APIRouter, HTTPException, Query

from database import get_connection
from timetable.schemas import TimetableSlotCreate, TimetableSlotUpdate


router = APIRouter(prefix="/timetable", tags=["Timetable"])


def format_time(value):
    if isinstance(value, time):
        return value.strftime("%H:%M")
    return str(value)[:5]


def duration_minutes(start_time, end_time):
    start = start_time.hour * 60 + start_time.minute
    end = end_time.hour * 60 + end_time.minute
    return end - start


def slot_row(row):
    duration = duration_minutes(row[8], row[9])
    return {
        "slot_id": row[0],
        "offering_id": row[1],
        "hall_id": row[2],
        "primary_instructor_id": row[3],
        "ta_instructor_id": row[4],
        "day_of_week": row[5],
        "start_time": format_time(row[8]),
        "end_time": format_time(row[9]),
        "is_active": bool(row[10]),
        "course_code": row[6],
        "course_name": row[7],
        "section_code": row[11],
        "lecturer_name": row[12],
        "ta_name": row[13],
        "duration_minutes": duration,
    }


@router.get("/weekly")
def get_weekly_timetable(
    semester_id: int = Query(gt=0),
    hall_id: int = Query(gt=0),
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT
                ts.slot_id,
                ts.offering_id,
                ts.hall_id,
                ts.primary_instructor_id,
                ts.ta_instructor_id,
                ts.day_of_week,
                c.course_code,
                c.course_name,
                ts.start_time,
                ts.end_time,
                ts.is_active,
                co.section_code,
                lecturer_person.full_name,
                ta_person.full_name
            FROM TimetableSlots ts
            INNER JOIN CourseOfferings co ON co.offering_id = ts.offering_id
            INNER JOIN Courses c ON c.course_id = co.course_id
            INNER JOIN Instructors lecturer
                ON lecturer.instructor_id = ts.primary_instructor_id
            INNER JOIN People lecturer_person
                ON lecturer_person.person_id = lecturer.person_id
            LEFT JOIN Instructors ta
                ON ta.instructor_id = ts.ta_instructor_id
            LEFT JOIN People ta_person
                ON ta_person.person_id = ta.person_id
            WHERE ts.hall_id = ?
              AND co.semester_id = ?
              AND ts.is_active = 1
            ORDER BY ts.day_of_week, ts.start_time
        """, hall_id, semester_id)

        return [slot_row(row) for row in cursor.fetchall()]
    finally:
        connection.close()


@router.get("/sessions/history")
def get_session_history(
    semester_id: int = Query(gt=0),
    hall_id: int | None = Query(default=None, gt=0),
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
                ls.session_id,
                ls.session_date,
                ls.scheduled_start,
                ls.scheduled_end,
                ls.actual_start,
                ls.actual_end,
                ls.session_status,
                lh.hall_id,
                lh.hall_name,
                lh.building,
                c.course_code,
                c.course_name,
                co.section_code,
                lecturer_person.full_name,
                ta_person.full_name,
                COUNT(sa.attendance_id),
                SUM(CASE WHEN sa.attendance_status = 'Present' THEN 1 ELSE 0 END),
                SUM(CASE WHEN sa.attendance_status = 'Late' THEN 1 ELSE 0 END)
            FROM LectureSessions ls
            INNER JOIN TimetableSlots ts ON ts.slot_id = ls.slot_id
            INNER JOIN CourseOfferings co ON co.offering_id = ts.offering_id
            INNER JOIN Courses c ON c.course_id = co.course_id
            INNER JOIN LectureHalls lh ON lh.hall_id = ts.hall_id
            INNER JOIN Instructors lecturer ON lecturer.instructor_id = ls.primary_instructor_id
            INNER JOIN People lecturer_person ON lecturer_person.person_id = lecturer.person_id
            LEFT JOIN Instructors ta ON ta.instructor_id = ls.ta_instructor_id
            LEFT JOIN People ta_person ON ta_person.person_id = ta.person_id
            LEFT JOIN StudentAttendance sa ON sa.session_id = ls.session_id
            WHERE co.semester_id = ?
              AND ls.session_date <= CAST(GETDATE() AS DATE)
              AND (? IS NULL OR lh.hall_id = ?)
              AND (
                    ? = ''
                    OR c.course_code LIKE ?
                    OR c.course_name LIKE ?
                    OR lh.hall_name LIKE ?
                    OR lecturer_person.full_name LIKE ?
                  )
            GROUP BY
                ls.session_id,
                ls.session_date,
                ls.scheduled_start,
                ls.scheduled_end,
                ls.actual_start,
                ls.actual_end,
                ls.session_status,
                lh.hall_id,
                lh.hall_name,
                lh.building,
                c.course_code,
                c.course_name,
                co.section_code,
                lecturer_person.full_name,
                ta_person.full_name
            ORDER BY ls.session_date DESC, ls.scheduled_start DESC
            OFFSET ? ROWS
            FETCH NEXT ? ROWS ONLY
        """,
            semester_id,
            hall_id,
            hall_id,
            search,
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            offset,
            limit,
        )

        items = []
        for row in cursor.fetchall():
            items.append({
                "session_id": row[0],
                "session_date": str(row[1]),
                "scheduled_start": format_time(row[2]),
                "scheduled_end": format_time(row[3]),
                "actual_start": row[4].isoformat() if row[4] else None,
                "actual_end": row[5].isoformat() if row[5] else None,
                "session_status": row[6],
                "hall_id": row[7],
                "hall_name": row[8],
                "building": row[9],
                "course_code": row[10],
                "course_name": row[11],
                "section_code": row[12],
                "lecturer_name": row[13],
                "ta_name": row[14],
                "lecturer_attended": row[4] is not None,
                "student_attendance_count": row[15] or 0,
                "present_count": row[16] or 0,
                "late_count": row[17] or 0,
            })

        cursor.execute("""
            SELECT COUNT(*)
            FROM (
                SELECT ls.session_id
                FROM LectureSessions ls
                INNER JOIN TimetableSlots ts ON ts.slot_id = ls.slot_id
                INNER JOIN CourseOfferings co ON co.offering_id = ts.offering_id
                INNER JOIN Courses c ON c.course_id = co.course_id
                INNER JOIN LectureHalls lh ON lh.hall_id = ts.hall_id
                INNER JOIN Instructors lecturer ON lecturer.instructor_id = ls.primary_instructor_id
                INNER JOIN People lecturer_person ON lecturer_person.person_id = lecturer.person_id
                WHERE co.semester_id = ?
                  AND ls.session_date <= CAST(GETDATE() AS DATE)
                  AND (? IS NULL OR lh.hall_id = ?)
                  AND (
                        ? = ''
                        OR c.course_code LIKE ?
                        OR c.course_name LIKE ?
                        OR lh.hall_name LIKE ?
                        OR lecturer_person.full_name LIKE ?
                      )
            ) history
        """,
            semester_id,
            hall_id,
            hall_id,
            search,
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
        )
        total = cursor.fetchone()[0]

        return {
            "items": items,
            "total": total,
            "offset": offset,
            "limit": limit,
        }
    finally:
        connection.close()


@router.get("/sessions/{session_id}/students")
def get_session_student_attendance(session_id: int):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT
                sa.attendance_id,
                p.university_id,
                p.full_name,
                sa.attendance_status,
                sa.check_in_time,
                sa.verification_method
            FROM StudentAttendance sa
            INNER JOIN Students s ON s.student_id = sa.student_id
            INNER JOIN People p ON p.person_id = s.person_id
            WHERE sa.session_id = ?
            ORDER BY sa.check_in_time
        """, session_id)

        return [{
            "attendance_id": row[0],
            "university_id": row[1],
            "full_name": row[2],
            "attendance_status": row[3],
            "check_in_time": row[4].isoformat(),
            "verification_method": row[5],
        } for row in cursor.fetchall()]
    finally:
        connection.close()


@router.get("/offerings")
def get_available_offerings(
    semester_id: int = Query(gt=0),
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
            ORDER BY c.course_code, co.section_code
            OFFSET ? ROWS
            FETCH NEXT ? ROWS ONLY
        """,
            semester_id,
            search,
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            offset,
            limit,
        )

        items = [{
            "offering_id": row[0],
            "course_id": row[1],
            "course_code": row[2],
            "course_name": row[3],
            "section_code": row[4],
        } for row in cursor.fetchall()]

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
        """,
            semester_id,
            search,
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
        )
        total = cursor.fetchone()[0]
        return {
            "items": items,
            "total": total,
            "offset": offset,
            "limit": limit,
        }
    finally:
        connection.close()


@router.get("/offerings/{offering_id}/instructors")
def get_offering_instructors(offering_id: int):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT
                io.instructor_id,
                p.full_name,
                io.instructor_role,
                i.department
            FROM InstructorOfferings io
            INNER JOIN Instructors i ON i.instructor_id = io.instructor_id
            INNER JOIN People p ON p.person_id = i.person_id
            WHERE io.offering_id = ?
            ORDER BY io.instructor_role, p.full_name
        """, offering_id)

        lecturers = []
        tas = []
        for row in cursor.fetchall():
            instructor = {
                "instructor_id": row[0],
                "full_name": row[1],
                "role": row[2],
                "department": row[3],
            }
            if row[2] == "Lecturer":
                lecturers.append(instructor)
            elif row[2] == "TA":
                tas.append(instructor)

        return {"lecturers": lecturers, "tas": tas}
    finally:
        connection.close()


@router.get("/slots/{slot_id}")
def get_slot(slot_id: int):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT
                ts.slot_id,
                ts.offering_id,
                ts.hall_id,
                ts.primary_instructor_id,
                ts.ta_instructor_id,
                ts.day_of_week,
                c.course_code,
                c.course_name,
                ts.start_time,
                ts.end_time,
                ts.is_active,
                co.section_code,
                lecturer_person.full_name,
                ta_person.full_name
            FROM TimetableSlots ts
            INNER JOIN CourseOfferings co ON co.offering_id = ts.offering_id
            INNER JOIN Courses c ON c.course_id = co.course_id
            INNER JOIN Instructors lecturer ON lecturer.instructor_id = ts.primary_instructor_id
            INNER JOIN People lecturer_person ON lecturer_person.person_id = lecturer.person_id
            LEFT JOIN Instructors ta ON ta.instructor_id = ts.ta_instructor_id
            LEFT JOIN People ta_person ON ta_person.person_id = ta.person_id
            WHERE ts.slot_id = ?
        """, slot_id)
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Timetable slot not found.")
        return slot_row(row)
    finally:
        connection.close()


def validate_slot(
    cursor,
    semester_id,
    offering_id,
    hall_id,
    lecturer_id,
    ta_id,
    day_of_week,
    start_time,
    end_time,
    slot_id=None,
):
    cursor.execute("""
        SELECT 1
        FROM LectureHalls
        WHERE hall_id = ?
    """, hall_id)
    if cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="Lecture hall not found.")

    cursor.execute("""
        SELECT co.semester_id
        FROM CourseOfferings co
        WHERE co.offering_id = ?
    """, offering_id)
    offering = cursor.fetchone()
    if offering is None:
        raise HTTPException(status_code=404, detail="Course offering not found.")
    if offering[0] != semester_id:
        raise HTTPException(
            status_code=400,
            detail="The course offering does not belong to the selected semester.",
        )

    if ta_id is not None:
        raise HTTPException(
            status_code=400,
            detail="Choose either a lecturer or a TA for the hall.",
        )

    cursor.execute("""
        SELECT 1
        FROM InstructorOfferings io
        INNER JOIN Instructors i ON i.instructor_id = io.instructor_id
        WHERE io.offering_id = ?
          AND io.instructor_id = ?
          AND io.instructor_role = i.instructor_type
          AND io.instructor_role IN ('Lecturer', 'TA')
    """, offering_id, lecturer_id)
    if cursor.fetchone() is None:
        raise HTTPException(
            status_code=400,
            detail="The assigned instructor is not assigned to this offering.",
        )

    cursor.execute("""
        SELECT slot_id
        FROM TimetableSlots WITH (UPDLOCK, HOLDLOCK)
        WHERE hall_id = ? AND day_of_week = ? AND is_active = 1
          AND (? IS NULL OR slot_id <> ?)
    """, hall_id, day_of_week, slot_id, slot_id)
    cursor.fetchall()

    cursor.execute("""
        SELECT ts.slot_id, c.course_code, ts.start_time, ts.end_time
        FROM TimetableSlots ts
        INNER JOIN CourseOfferings co ON co.offering_id = ts.offering_id
        INNER JOIN Courses c ON c.course_id = co.course_id
        WHERE ts.hall_id = ?
          AND ts.day_of_week = ?
          AND ts.is_active = 1
          AND (? IS NULL OR ts.slot_id <> ?)
          AND ts.start_time < ?
          AND ts.end_time > ?
    """,
        hall_id,
        day_of_week,
        slot_id,
        slot_id,
        end_time,
        start_time,
    )
    conflict = cursor.fetchone()
    if conflict is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Hall is occupied by {conflict[1]} from {format_time(conflict[2])} to {format_time(conflict[3])}.",
        )

    cursor.execute("""
        SELECT ts.slot_id
        FROM TimetableSlots ts WITH (UPDLOCK, HOLDLOCK)
        WHERE ts.day_of_week = ?
          AND ts.is_active = 1
          AND (? IS NULL OR ts.slot_id <> ?)
          AND (
                ts.primary_instructor_id = ?
                OR ts.ta_instructor_id = ?
              )
          AND ts.start_time < ?
          AND ts.end_time > ?
    """,
        day_of_week,
        slot_id,
        slot_id,
        lecturer_id,
        lecturer_id,
        end_time,
        start_time,
    )
    conflict = cursor.fetchone()
    if conflict is not None:
        raise HTTPException(
            status_code=409,
            detail="Lecturer is already scheduled at this time.",
        )

    if ta_id is not None:
        cursor.execute("""
            SELECT ts.slot_id
            FROM TimetableSlots ts WITH (UPDLOCK, HOLDLOCK)
            WHERE ts.day_of_week = ?
              AND ts.is_active = 1
              AND (? IS NULL OR ts.slot_id <> ?)
              AND (
                    ts.primary_instructor_id = ?
                    OR ts.ta_instructor_id = ?
                  )
              AND ts.start_time < ?
              AND ts.end_time > ?
        """,
            day_of_week,
            slot_id,
            slot_id,
            ta_id,
            ta_id,
            end_time,
            start_time,
        )
        conflict = cursor.fetchone()
        if conflict is not None:
            raise HTTPException(
                status_code=409,
                detail="TA is already scheduled at this time.",
            )


@router.post("/slots", status_code=201)
def create_slot(slot: TimetableSlotCreate):
    connection = get_connection()
    try:
        connection.autocommit = False
        cursor = connection.cursor()
        validate_slot(
            cursor,
            slot.semester_id,
            slot.offering_id,
            slot.hall_id,
            slot.primary_instructor_id,
            slot.ta_instructor_id,
            slot.day_of_week,
            slot.start_time,
            slot.end_time,
        )
        cursor.execute("""
            INSERT INTO TimetableSlots
                (offering_id, hall_id, primary_instructor_id,
                 ta_instructor_id, day_of_week, start_time, end_time,
                 is_active)
            OUTPUT INSERTED.slot_id
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """,
            slot.offering_id,
            slot.hall_id,
            slot.primary_instructor_id,
            slot.ta_instructor_id,
            slot.day_of_week,
            slot.start_time,
            slot.end_time,
        )
        slot_id = cursor.fetchone()[0]
        connection.commit()
        return {
            "message": "Timetable slot created successfully.",
            "slot_id": slot_id,
        }
    except HTTPException:
        connection.rollback()
        raise
    except pyodbc.IntegrityError:
        connection.rollback()
        raise HTTPException(
            status_code=400,
            detail="Unable to create the timetable slot. Check the submitted values.",
        )
    finally:
        connection.close()


@router.put("/slots/{slot_id}")
def update_slot(slot_id: int, slot: TimetableSlotUpdate, semester_id: int = Query(gt=0), hall_id: int = Query(gt=0)):
    connection = get_connection()
    try:
        connection.autocommit = False
        cursor = connection.cursor()
        cursor.execute("""
            SELECT hall_id
            FROM TimetableSlots
            WHERE slot_id = ? AND is_active = 1
        """, slot_id)
        existing = cursor.fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Timetable slot not found.")

        validate_slot(
            cursor,
            semester_id,
            slot.offering_id,
            hall_id,
            slot.primary_instructor_id,
            slot.ta_instructor_id,
            slot.day_of_week,
            slot.start_time,
            slot.end_time,
            slot_id,
        )
        cursor.execute("""
            UPDATE TimetableSlots
            SET offering_id = ?,
                hall_id = ?,
                primary_instructor_id = ?,
                ta_instructor_id = ?,
                day_of_week = ?,
                start_time = ?,
                end_time = ?
            WHERE slot_id = ? AND is_active = 1
        """,
            slot.offering_id,
            hall_id,
            slot.primary_instructor_id,
            slot.ta_instructor_id,
            slot.day_of_week,
            slot.start_time,
            slot.end_time,
            slot_id,
        )
        connection.commit()
        return {"message": "Timetable slot updated successfully."}
    except HTTPException:
        connection.rollback()
        raise
    except pyodbc.IntegrityError:
        connection.rollback()
        raise HTTPException(status_code=400, detail="Unable to update the timetable slot.")
    finally:
        connection.close()


@router.delete("/slots/{slot_id}")
def delete_slot(slot_id: int):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE TimetableSlots
            SET is_active = 0
            WHERE slot_id = ? AND is_active = 1
        """, slot_id)
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Active timetable slot not found.")
        connection.commit()
        return {"message": "Timetable slot removed successfully."}
    finally:
        connection.close()
