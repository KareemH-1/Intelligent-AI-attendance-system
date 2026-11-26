import os
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from auth.router import change_password, login
from auth.schemas import LoginRequest, PasswordChangeRequest
from auth.security import hash_password, verify_password


def test_password_change_accepts_eight_character_password():
    request = PasswordChangeRequest(
        current_password="temporary",
        new_password="12345678",
    )

    assert request.new_password == "12345678"


def test_password_change_rejects_password_shorter_than_eight_characters():
    with pytest.raises(ValueError):
        PasswordChangeRequest(
            current_password="temporary",
            new_password="1234567",
        )


def test_password_change_accepts_reusing_current_password():
    current_password = "samepass"
    connection = FakePasswordConnection(hash_password(current_password))

    with patch("auth.router.get_connection", return_value=connection):
        response = change_password(
            PasswordChangeRequest(
                current_password=current_password,
                new_password=current_password,
            ),
            {"account_id": 7},
        )

    assert response == {"message": "Password changed successfully."}
    assert verify_password(current_password, connection.cursor_instance.updated_hash)
    assert "must_change_password = 0" in connection.cursor_instance.update_query
    assert connection.committed


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.query = ""
        self.parameters = ()

    def execute(self, query, *parameters):
        self.query = query
        self.parameters = parameters

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, rows):
        self.fake_cursor = FakeCursor(rows)
        self.closed = False

    def cursor(self):
        return self.fake_cursor

    def close(self):
        self.closed = True


class FakePasswordCursor:
    def __init__(self, stored_hash):
        self.stored_hash = stored_hash
        self.updated_hash = None
        self.update_query = ""

    def execute(self, query, *parameters):
        if query.lstrip().startswith("UPDATE"):
            self.update_query = query
            self.updated_hash = parameters[0]

    def fetchone(self):
        return (self.stored_hash,)


class FakePasswordConnection:
    def __init__(self, stored_hash):
        self.cursor_instance = FakePasswordCursor(stored_hash)
        self.committed = False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.committed = True

    def rollback(self):
        pass

    def close(self):
        pass


@pytest.mark.parametrize("identifier", ["U12345", "admin@example.edu"])
def test_login_uses_university_id_or_email(identifier):
    stored_hash = hash_password("Admin#123")
    row = (1, stored_hash, True, True, "internal-name", "Admin", "Admin User")
    connection = FakeConnection([row])

    with patch("auth.router.get_connection", return_value=connection):
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "x" * 48}):
            response = login(LoginRequest(identifier=identifier, password="Admin#123"))

    assert response.user.account_id == 1
    assert response.user.must_change_password is True
    assert "WHERE p.university_id = ? OR p.email = ?" in connection.fake_cursor.query
    assert "WHERE ua.username" not in connection.fake_cursor.query
    assert connection.fake_cursor.parameters == (identifier, identifier)
    assert connection.closed


def test_login_rejects_non_id_email_identifier():
    connection = FakeConnection([])

    with patch("auth.router.get_connection", return_value=connection):
        with pytest.raises(HTTPException) as error:
            login(LoginRequest(identifier="internal-name", password="Admin#123"))

    assert error.value.status_code == 401
    assert connection.closed


def test_login_rejects_ambiguous_identifier():
    row = (1, hash_password("Admin#123"), True, True, "name", "Admin", "Admin User")
    connection = FakeConnection([row, row])

    with patch("auth.router.get_connection", return_value=connection):
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "x" * 48}):
            with pytest.raises(HTTPException) as error:
                login(LoginRequest(identifier="conflict", password="Admin#123"))

    assert error.value.status_code == 401
    assert connection.closed
