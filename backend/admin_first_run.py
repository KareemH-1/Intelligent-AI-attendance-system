from auth.security import DEFAULT_INITIAL_PASSWORD, hash_password
from database import get_connection


def required_input(label: str, max_length: int) -> str:
    value = input(f"{label}: ").strip()
    if not value or len(value) > max_length:
        raise ValueError(f"{label} must contain 1 to {max_length} characters.")
    return value


def create_initial_admin() -> None:
    university_id = required_input("University ID", 30)
    full_name = required_input("Full name", 150)
    username = required_input("Admin username", 100)
    email = input("Email (optional): ").strip() or None
    if email is not None and len(email) > 150:
        raise ValueError("Email must be at most 150 characters.")

    connection = get_connection()
    try:
        connection.autocommit = False
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT role_id
            FROM Roles
            WHERE role_name = 'Admin'
            """
        )
        role = cursor.fetchone()
        if role is None:
            raise RuntimeError("The Admin role is not configured in Roles.")

        cursor.execute(
            """
            SELECT TOP 1 ua.account_id
            FROM UserAccounts ua
            INNER JOIN Roles r ON r.role_id = ua.role_id
            WHERE r.role_name = 'Admin'
            """
        )
        if cursor.fetchone() is not None:
            raise RuntimeError(
                "An Admin account already exists; bootstrap was not performed."
            )

        cursor.execute(
            """
            INSERT INTO People (university_id, full_name, email)
            OUTPUT INSERTED.person_id
            VALUES (?, ?, ?)
            """,
            university_id,
            full_name,
            email,
        )
        person_id = cursor.fetchone()[0]
        cursor.execute(
            """
            INSERT INTO UserAccounts
                (person_id, role_id, username, password_hash,
                 is_active, must_change_password)
            VALUES (?, ?, ?, ?, 1, 1)
            """,
            person_id,
            role[0],
            username,
            hash_password(DEFAULT_INITIAL_PASSWORD),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    print(f"Admin account '{username}' created.")
    print(f"Temporary password: {DEFAULT_INITIAL_PASSWORD}")
    print("Change this password at first login.")


if __name__ == "__main__":
    create_initial_admin()
