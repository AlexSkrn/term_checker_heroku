#!/usr/bin/env python3
import os
import psycopg2
from config import config


def get_bitext():
    """Provide sample data for development."""
    return [
        ('Original texts are usually good texts, but sometimes are bad texts.',
         'Переведенные тексты - это обычно плохие тексты, но иногда - хорошие тексты.'),
        ('Translated texts are usually bad texts, but sometimes are good texts.',
         'Оригинальные тексты - это обычно хорошие тексты, но иногда - плохие тексты.'),
        ('The five boxing wizards jump quickly.', 'Некоторый текст'),
        ('How vexingly quick daft zebras jump!', 'Некоторый текст'),
        ('Bright vixens jump; dozy fowl quack.', 'Некоторый текст'),
        ]


def create_table(direction, data):
    """Create and populate a PostgreSQL database table with data."""
    if direction == 'eng-rus':
        src_lang, trg_lang = 'english', 'russian'
    elif direction == 'rus-eng':
        src_lang, trg_lang = 'russian', 'english'

    table_name = 'bitext'

    create_search_config = (
        """
        CREATE TEXT SEARCH DICTIONARY public.{}_nostop (
            TEMPLATE = snowball, Language = {}
            )
        """,
        """
        CREATE TEXT SEARCH CONFIGURATION public.{}_nostop
        ( COPY = pg_catalog.{} )
        """,
        """
        ALTER TEXT SEARCH CONFIGURATION public.{}_nostop
            ALTER MAPPING FOR asciiword,
                          asciihword,
                          hword_asciipart,
                          hword,
                          hword_part,
                          word
            WITH {}_nostop
            """
            )

    add_rus_synonyms_config = (
        """
        CREATE TEXT SEARCH DICTIONARY my_synonym (
            TEMPLATE = synonym,
            SYNONYMS = my_synonyms
            )
        """,
        """
        ALTER TEXT SEARCH CONFIGURATION public.russian_nostop
            ALTER MAPPING FOR word
            WITH my_synonym, russian_nostop, russian_stem
        """
        )

    create_tab_commands = (
        """
        DROP TABLE IF EXISTS {}
        """
        .format(table_name),
        """
        CREATE TABLE {} (
            id SERIAL,
            src TEXT,
            src_tokens TSVECTOR,
            trg TEXT,
            trg_tokens TSVECTOR
        )
        """
        .format(table_name)
        )
    insert_command = """INSERT INTO {} (src, trg) VALUES(%s, %s)""".format(table_name)

    update_command = (
        """
        UPDATE {} as t
        SET src_tokens = to_tsvector('public.{}_nostop', t.src),
            trg_tokens = to_tsvector('public.{}_nostop', t.trg)
        """
        .format(table_name, src_lang, trg_lang)
        )
    conn = None
    try:
        print('Connecting to the PostgreSQL database...')
        try:
            conn = psycopg2.connect(os.environ['DATABASE_URL'])
        except KeyError:
            conn = psycopg2.connect(**config())
            local_db = True
        with conn:
            with conn.cursor() as cur:
                for lang in (src_lang, trg_lang):
                    cur.execute("DROP TEXT SEARCH DICTIONARY IF EXISTS public.{}_nostop CASCADE".format(lang))
                    for command in create_search_config:
                        cur.execute(command.format(lang, lang))
                if local_db:
                    cur.execute("DROP TEXT SEARCH DICTIONARY IF EXISTS public.my_synonym CASCADE".format(lang))
                    for command in add_rus_synonyms_config:
                        cur.execute(command)

                for command in create_tab_commands:
                    cur.execute(command)
                cur.executemany(insert_command, data)
                cur.execute(update_command)
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
            print('Database connection closed.')


if __name__ == '__main__':
    create_table('eng-rus', get_bitext())
