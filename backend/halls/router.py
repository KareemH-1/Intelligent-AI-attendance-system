import pyodbc
import hashlib
import secrets
from fastapi import APIRouter, HTTPException, Query

from database import get_connection
from halls.schemas import (
    HallCreate,
    HallUpdate,
    TerminalPasswordUpdate,
    TerminalStatusUpdate,
)


router = APIRouter(prefix="/halls", tags=["Lecture Halls"])


def is_unique_violation(error):
    message = str(error)
    return "2627" in message or "2601" in message


def hash_terminal_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    ).hex()
    return f"pbkdf2_sha256${salt}${digest}"


def ensure_hall_terminal(cursor, hall_id, password):
    cursor.execute("""
        SELECT hall_name
        FROM LectureHalls
        WHERE hall_id = ?
    """, hall_id)
    hall = cursor.fetchone()
    if hall is None:
        raise HTTPException(status_code=404, detail="Lecture hall not found.")

    cursor.execute("""
        SELECT terminal_id
        FROM HallTerminals
        WHERE hall_id = ?
    """, hall_id)
    terminal = cursor.fetchone()
    if terminal is not None:
        return terminal[0]

    terminal_code = f"HALL-{hall_id}"
    device_name = f"{hall[0].strip()} Hall Terminal"
    cursor.execute("""
        INSERT INTO HallTerminals
            (hall_id, terminal_code, device_name, device_key_hash, is_active)
        OUTPUT INSERTED.terminal_id
        VALUES (?, ?, ?, ?, 1)
    """,
        hall_id,
        terminal_code,
        device_name,
        hash_terminal_password(password),
    )
    return cursor.fetchone()[0]


def row_to_hall(row):
    return {
        "hall_id": row[0],
        "hall_name": row[1],
        "building": row[2],
        "capacity": row[3],
        "terminal_id": row[4],
        "terminal_code": row[5],
        "terminal_active": bool(row[6]) if row[6] is not None else None,
        "device_name": row[7],
    }


@router.get("")
def get_halls(search: str = Query(default="", max_length=150)):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        search = search.strip()
        cursor.execute("""
            SELECT
                lh.hall_id,
                lh.hall_name,
                lh.building,
                lh.capacity,
                ht.terminal_id,
                ht.terminal_code,
                ht.is_active,
                ht.device_name
            FROM LectureHalls lh
            LEFT JOIN HallTerminals ht ON ht.hall_id = lh.hall_id
            WHERE
                ? = ''
                OR lh.hall_name LIKE ?
                OR lh.building LIKE ?
            ORDER BY lh.building, lh.hall_name
        """,
            search,
            f"%{search}%",
            f"%{search}%",
        )
        return [row_to_hall(row) for row in cursor.fetchall()]
    finally:
        connection.close()


@router.get("/{hall_id}")
def get_hall(hall_id: int):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT
                lh.hall_id,
                lh.hall_name,
                lh.building,
                lh.capacity,
                ht.terminal_id,
                ht.terminal_code,
                ht.is_active,
                ht.device_name
            FROM LectureHalls lh
            LEFT JOIN HallTerminals ht ON ht.hall_id = lh.hall_id
            WHERE lh.hall_id = ?
        """, hall_id)
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Lecture hall not found.")
        return row_to_hall(row)
    finally:
        connection.close()


@router.get("/{hall_id}/terminal")
def get_hall_terminal(hall_id: int):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT
                ht.terminal_id,
                ht.terminal_code,
                ht.device_name,
                ht.is_active,
                ht.last_seen,
                ht.created_at
            FROM HallTerminals ht
            WHERE ht.hall_id = ?
        """, hall_id)
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Hall terminal not found.")
        return {
            "terminal_id": row[0],
            "terminal_code": row[1],
            "device_name": row[2],
            "is_active": bool(row[3]),
            "last_seen": row[4],
            "created_at": row[5],
        }
    finally:
        connection.close()


@router.patch("/{hall_id}/terminal/password")
def reset_hall_terminal_password(
    hall_id: int,
    request: TerminalPasswordUpdate,
):
    connection = get_connection()
    try:
        connection.autocommit = False
        cursor = connection.cursor()
        terminal_id = ensure_hall_terminal(
            cursor,
            hall_id,
            request.terminal_password,
        )
        cursor.execute("""
            UPDATE HallTerminals
            SET device_key_hash = ?
            WHERE terminal_id = ?
        """,
            hash_terminal_password(request.terminal_password),
            terminal_id,
        )
        connection.commit()
        return {"message": "Hall terminal password updated successfully."}
    except HTTPException:
        connection.rollback()
        raise
    except pyodbc.IntegrityError:
        connection.rollback()
        raise HTTPException(
            status_code=409,
            detail="A Hall Terminal with this code already exists.",
        )
    finally:
        connection.close()


@router.patch("/{hall_id}/terminal/status")
def update_hall_terminal_status(
    hall_id: int,
    request: TerminalStatusUpdate,
):
    connection = get_connection()
    try:
        connection.autocommit = False
        cursor = connection.cursor()
        terminal_id = ensure_hall_terminal(
            cursor,
            hall_id,
            "ChangeMe123",
        )
        cursor.execute("""
            UPDATE HallTerminals
            SET is_active = ?
            WHERE terminal_id = ?
        """, 1 if request.is_active else 0, terminal_id)
        connection.commit()
        return {
            "message": (
                "Hall terminal activated successfully."
                if request.is_active
                else "Hall terminal deactivated successfully."
            ),
            "is_active": request.is_active,
        }
    finally:
        connection.close()


@router.post("", status_code=201)
def create_hall(hall: HallCreate):
    connection = get_connection()
    try:
        connection.autocommit = False
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO LectureHalls (hall_name, building, capacity)
            OUTPUT INSERTED.hall_id
            VALUES (?, ?, ?)
        """,
            hall.hall_name.strip(),
            hall.building.strip(),
            hall.capacity,
        )
        hall_id = cursor.fetchone()[0]

        terminal_code = f"HALL-{hall_id}"
        device_name = f"{hall.hall_name.strip()} Hall Terminal"
        cursor.execute("""
            INSERT INTO HallTerminals
                (hall_id, terminal_code, device_name, device_key_hash, is_active)
            OUTPUT INSERTED.terminal_id
            VALUES (?, ?, ?, ?, 1)
        """,
            hall_id,
            terminal_code,
            device_name,
            hash_terminal_password(hall.terminal_password),
        )
        terminal_id = cursor.fetchone()[0]
        connection.commit()
        return {
            "message": "Lecture hall created successfully.",
            "hall_id": hall_id,
            "terminal_id": terminal_id,
            "terminal_code": terminal_code,
        }
    except pyodbc.IntegrityError as error:
        connection.rollback()
        if is_unique_violation(error):
            raise HTTPException(
                status_code=409,
                detail="A hall with this name already exists in the building.",
            )
        raise HTTPException(
            status_code=400,
            detail="Please enter valid hall information.",
        )
    finally:
        connection.close()


@router.put("/{hall_id}")
def update_hall(hall_id: int, hall: HallUpdate):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE LectureHalls
            SET hall_name = ?, building = ?, capacity = ?
            WHERE hall_id = ?
        """,
            hall.hall_name.strip(),
            hall.building.strip(),
            hall.capacity,
            hall_id,
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Lecture hall not found.")
        connection.commit()
        return {"message": "Lecture hall updated successfully."}
    except HTTPException:
        connection.rollback()
        raise
    except pyodbc.IntegrityError as error:
        connection.rollback()
        if is_unique_violation(error):
            raise HTTPException(
                status_code=409,
                detail="A hall with this name already exists in the building.",
            )
        raise HTTPException(status_code=400, detail="Invalid hall information.")
    finally:
        connection.close()


@router.delete("/{hall_id}")
def delete_hall(hall_id: int):
    connection = get_connection()
    try:
        connection.autocommit = False
        cursor = connection.cursor()
        cursor.execute("""
            DELETE FROM HallTerminals
            WHERE hall_id = ?
        """, hall_id)
        cursor.execute("""
            DELETE FROM LectureHalls
            WHERE hall_id = ?
        """, hall_id)
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Lecture hall not found.")
        connection.commit()
        return {"message": "Lecture hall deleted successfully."}
    except pyodbc.IntegrityError:
        connection.rollback()
        raise HTTPException(
            status_code=409,
            detail="This hall cannot be deleted because it is referenced by timetable slots or hall terminals.",
        )
    finally:
        connection.close()
