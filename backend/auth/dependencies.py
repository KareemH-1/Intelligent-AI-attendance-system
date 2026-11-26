from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt

from database import get_connection
from auth.security import decode_access_token


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_account(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    unauthorized = HTTPException(
        status_code=401,
        detail="Authentication is required.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized

    try:
        claims = decode_access_token(credentials.credentials)
        account_id = int(claims["sub"])
    except (jwt.JWTError, KeyError, TypeError, ValueError):
        raise unauthorized

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
                ua.account_id,
                ua.username,
                ua.is_active,
                ua.must_change_password,
                r.role_name,
                p.full_name
            FROM UserAccounts ua
            INNER JOIN Roles r ON r.role_id = ua.role_id
            INNER JOIN People p ON p.person_id = ua.person_id
            WHERE ua.account_id = ?
            """,
            account_id,
        )
        row = cursor.fetchone()
        if row is None or not row[2]:
            raise unauthorized

        return {
            "account_id": row[0],
            "username": row[1],
            "must_change_password": bool(row[3]),
            "role": row[4],
            "full_name": row[5],
        }
    finally:
        connection.close()


def require_admin(account: dict = Depends(get_current_account)) -> dict:
    if account["must_change_password"]:
        raise HTTPException(
            status_code=403,
            detail="Change your password before continuing.",
        )
    if account["role"] != "Admin":
        raise HTTPException(
            status_code=403,
            detail="Administrator access is required.",
        )
    return account
