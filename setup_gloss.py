#!/usr/bin/env python3
import os
import psycopg2
from config import config


def get_sample_gloss():
    """Provide sample glossary data for testing."""
    return [
            ("LNG & Marine Facilities Committee", "Комитет по СПГ и Морским Объектам"),
            ("Total E&P Holdings", "Total E&P Holdings"),
            ('Agency Agreement', 'Агентский договор'),
            ("Foreign Partners' Entrance Consideration", "Плата за Вхождение Иностранных Партнеров"),
            ('Completion', 'Завершение'),
            ('Completion of the Project', 'Завершение Проекта')
            ]


def create_gloss_table(direction, data):
    """Create and populate a PostgreSQL database glossary table with data."""
    if direction == 'eng-rus':
        src_lang, trg_lang = 'english', 'russian'
    elif direction == 'rus-eng':
        src_lang, trg_lang = 'russian', 'english'

    table_name = 'gloss'

    create_tab_commands = (
        """
        DROP TABLE IF EXISTS {}
        """
        .format(table_name),
        """
        CREATE TABLE {} (
            src_term TEXT,
            trg_term TEXT
        )
        """
        .format(table_name)
        )
    insert_command = """INSERT INTO {} (src_term, trg_term) VALUES(%s, %s)""".format(table_name)

    conn = None
    try:
        print('Connecting to the PostgreSQL database...')
        try:
            conn = psycopg2.connect(os.environ['DATABASE_URL'])
        except KeyError:
            conn = psycopg2.connect(**config())
        with conn:
            with conn.cursor() as cur:
                for command in create_tab_commands:
                    cur.execute(command)
                cur.executemany(insert_command, data)
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
            print('Database connection closed.')


if __name__ == '__main__':
    create_gloss_table('eng-rus', get_sample_gloss())
