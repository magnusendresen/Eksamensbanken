from datetime import date
import sqlalchemy
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String
from sqlalchemy import Integer, String, Boolean, Float, Text, ForeignKey, Date
from typing import get_origin, get_type_hints
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import typing


import psycopg2
from psycopg2 import sql

import logging

TYPE_MAP = {
    int: Integer,
    str: Text,
    float: Float,
    bool: Boolean,
    date: Date,
}

class DB:
    def __init__(self, database_url: str):
        self.connection = psycopg2.connect(database_url)
        self.connection.autocommit = True

        self.engine = create_engine(database_url)
        self.metadata = MetaData()

    def create_table(self, cls) -> None:
        columns = []

        type_hints = get_type_hints(cls)
        table_name = cls.__name__.lower()

        for attr, py_type in type_hints.items():
            # Handle primary key
            if attr == 'id':
                columns.append(Column('id', Integer, primary_key=True))
                continue

            # Handle list types as e.g. comma-separated Text
            origin = get_origin(py_type)
            if origin is list:
                columns.append(Column(attr, Text))
                continue

            # Handle foreign key relationships
            if isinstance(py_type, type) and hasattr(py_type, '__annotations__'):
                ref_table = py_type.__name__.lower()
                columns.append(
                    Column(
                        f"{ref_table}_id",
                        Integer,
                        ForeignKey(f"{ref_table}.id")
                    )
                )
                continue
            
            # Handle basic types
            col_type = TYPE_MAP.get(py_type, Text)
            columns.append(Column(attr, col_type))

        Table(table_name, self.metadata, *columns)


    def get_rows(self, cls, conditions: dict):
        table_name = cls.__name__.lower()
        type_hints = get_type_hints(cls)

        clauses = []
        values = []

        for attr, value in conditions.items():
            py_type = type_hints[attr]

            col, val = self._resolve_column_and_value(attr, py_type, value)
            if col is None:
                continue

            clauses.append(
                sql.SQL("{} = %s").format(sql.Identifier(col))
            )
            values.append(val)

        query = sql.SQL("SELECT * FROM {} WHERE {}").format(
            sql.Identifier(table_name),
            sql.SQL(" AND ").join(clauses)
        )

        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, values)
            rows = cursor.fetchall()
            return rows

    SKIP_ATTRS = {
        # tunge PDF / OCR runtime-objekter
        "raw_page",
        "raw_pdf",
    }

    def add_entity(self, obj) -> None:
        table_name = obj.__class__.__name__.lower()
        type_hints = get_type_hints(obj.__class__)

        columns = []
        values = []

        for attr, py_type in type_hints.items():
            if attr in DB.SKIP_ATTRS:
                continue
            col, val = self._resolve_column_and_value(
                attr,
                py_type,
                getattr(obj, attr, None)
            )
            if col is None:
                continue
            columns.append(col)
            values.append(val)

        with self.connection.cursor() as cursor:
            query = sql.SQL(
                "INSERT INTO {} ({}) VALUES ({}) RETURNING id"
            ).format(
                sql.Identifier(table_name),
                sql.SQL(", ").join(map(sql.Identifier, columns)),
                sql.SQL(", ").join(sql.Placeholder() * len(values))
            )

            cursor.execute(query, values)
            obj.id = cursor.fetchone()[0]


    def set_values(self, obj, attrs: list[str]) -> None:
        table_name = obj.__class__.__name__.lower()
        type_hints = get_type_hints(obj.__class__)

        sets = []
        values = []

        for attr in attrs:
            py_type = type_hints[attr]
            value = getattr(obj, attr)

            col, val = self._resolve_column_and_value(attr, py_type, value)
            if col is None:
                continue

            sets.append(sql.SQL("{} = %s").format(sql.Identifier(col)))
            values.append(val)

        values.append(obj.id)

        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            query = sql.SQL("UPDATE {} SET {} WHERE id = %s").format(
                sql.Identifier(table_name),
                sql.SQL(", ").join(sets)
            )
            cursor.execute(query, values)


    def _resolve_column_and_value(self, attr: str, py_type, value):
        """
        Returnerer (column_name, sql_value) basert på samme regler som create_table
        """
        # Primary key håndteres ikke her
        if attr == "id":
            return None, None

        origin = get_origin(py_type)

        # list[...] → Text
        if origin is list:
            return attr, ",".join(map(str, value)) if value is not None else None

        # Foreign key (klasse med __annotations__)
        if isinstance(py_type, type) and hasattr(py_type, "__annotations__"):
            ref_table = py_type.__name__.lower()
            return f"{ref_table}_id", getattr(value, "id", None)

        # Vanlig kolonne
        return attr, value
    
    def select_children(
        self,
        parent_cls,
        child_cls,
        parent_id: int,
        order_by: list[str] | None = None,
    ) -> list[typing.Dict]:
        parent_table = parent_cls.__name__.lower()
        child_table = child_cls.__name__.lower()
        fk_col = f"{parent_table}_id"

        order_sql = ""
        if order_by:
            order_sql = " ORDER BY " + ", ".join(
                f"{child_table}.{col}" for col in order_by
            )

        query = f"""
            SELECT {child_table}.*
            FROM {child_table}
            JOIN {parent_table}
            ON {child_table}.{fk_col} = {parent_table}.id
            WHERE {parent_table}.id = %s
            {order_sql}
        """

        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, (parent_id,))
            return cursor.fetchall()
        
    def create_relation_table(self, cls: type) -> None:
        Table(
            f"{cls.__name__.lower()}_relation",
            self.metadata,
            Column('left_id', Integer, ForeignKey(f'{cls.__name__.lower()}.id')),
            Column('right_id', Integer, ForeignKey(f'{cls.__name__.lower()}.id')),
        )

    def delete_tables(self):
        print('⚠️  This will DROP ALL TABLES in the current schema.')
        answer = input('Are you sure? If so type "y": ')

        if answer != "y":
            print("Aborted.")
            return

        with self.connection.cursor() as cursor:
            cursor.execute("""
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
            """)
            tables = cursor.fetchall()

            for (table,) in tables:
                cursor.execute(
                    sql.SQL("DROP TABLE IF EXISTS {} CASCADE")
                    .format(sql.Identifier(table))
                )

        self.connection.commit()
        print("All tables deleted.")


