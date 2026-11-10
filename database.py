
import os
import sqlite3

import psycopg
from psycopg.rows import dict_row


DATABASE = "ridesync.db"


class PostgresConnection:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, query, parameters=()):
        query = query.replace("?", "%s")
        return self.connection.execute(query, parameters)

    def __getattr__(self, name):
        return getattr(self.connection, name)


def get_db_connection():
    database_url = os.environ.get("DATABASE_URL")

    if database_url:
        database_url = database_url.replace(
            "postgres://",
            "postgresql://",
            1
        )

        connection = psycopg.connect(
            database_url,
            row_factory=dict_row
        )

        return PostgresConnection(connection)

    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def is_postgres():
    return bool(os.environ.get("DATABASE_URL"))


DatabaseError = (sqlite3.Error, psycopg.Error)
IntegrityError = (sqlite3.IntegrityError, psycopg.IntegrityError)
