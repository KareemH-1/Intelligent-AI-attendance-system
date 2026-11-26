from fastapi import APIRouter, Depends, HTTPException

from auth.dependencies import get_current_account
from auth.schemas import (
    AuthenticatedUser,
    LoginRequest,
    LoginResponse,
    PasswordChangeRequest,
)
from auth.security import create_access_token, hash_password, verify_password
from database import get_connection


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT TOP (2)
                ua.account_id,
                ua.password_hash,
                ua.is_active,
                ua.must_change_password,
                ua.username,
                r.role_name,
                p.full_name
            FROM UserAccounts ua
            INNER JOIN Roles r ON r.role_id = ua.role_id
            INNER JOIN People p ON p.person_id = ua.person_id
            WHERE p.university_id = ? OR p.email = ?
            """,
            request.identifier.strip(),
            request.identifier.strip(),
        )
        matches = cursor.fetchall()
        row = matches[0] if len(matches) == 1 else None
        if (
            row is None
            or not row[2]
            or not verify_password(request.password, row[1])
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid ID/email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = AuthenticatedUser(
            account_id=row[0],
            username=row[4],
            full_name=row[6],
            role=row[5],
            must_change_password=bool(row[3]),
        )
        return LoginResponse(
            access_token=create_access_token(row[0]),
            user=user,
        )
    finally:
        connection.close()


@router.get("/me", response_model=AuthenticatedUser)
def get_me(account: dict = Depends(get_current_account)):
    return account


@router.post("/change-password")
def change_password(
    request: PasswordChangeRequest,
    account: dict = Depends(get_current_account),
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT password_hash
            FROM UserAccounts
            WHERE account_id = ?
            """,
            account["account_id"],
        )
        row = cursor.fetchone()
        if row is None or not verify_password(request.current_password, row[0]):
            raise HTTPException(
                status_code=400,
                detail="Current password is incorrect.",
            )

        cursor.execute(
            """
            UPDATE UserAccounts
            SET password_hash = ?, must_change_password = 0
            WHERE account_id = ?
            """,
            hash_password(request.new_password),
            account["account_id"],
        )
        connection.commit()
        return {"message": "Password changed successfully."}
    except HTTPException:
        connection.rollback()
        raise
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
