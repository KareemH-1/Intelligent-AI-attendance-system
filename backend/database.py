
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    driver = os.getenv("DB_DRIVER")
    server = os.getenv("DB_SERVER")
    database = os.getenv("DB_DATABASE")

    trusted_connection = os.getenv(
        "DB_TRUSTED_CONNECTION", "true"
    ).lower() == "true"

    trust_certificate = os.getenv(
        "DB_TRUST_SERVER_CERTIFICATE", "true"
    ).lower() == "true"

    if not driver or not server or not database:
        raise ValueError("database conf isnt in env")

    connection_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"Encrypt=yes;"
        f"TrustServerCertificate={'yes' if trust_certificate else 'no'};"
    )

    if trusted_connection:
        connection_string += "Trusted_Connection=yes;"
    else:
        username = os.getenv("DB_USERNAME")
        password = os.getenv("DB_PASSWORD")

        if not username or not password:
            raise ValueError(
                "dataase username and pass arent in env"
            )

        connection_string += f"UID={{{username}}};"
        connection_string += f"PWD={{{password.replace('}', '}}')}}};"

    return pyodbc.connect(connection_string, timeout=5)
