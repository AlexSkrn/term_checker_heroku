#!/usr/bin/env python3
import os
import psycopg2
from config import config

# Bitex-related queries
CREATE_SEARCH_CONFIG = (
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

ADD_RUS_SYNONYMS_CONFIG = (
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

CREATE_TAB_COMMANDS = (
    """
    DROP TABLE IF EXISTS {}
    """,
    """
    CREATE TABLE {} (
        id SERIAL,
        src TEXT,
        src_tokens TSVECTOR,
        trg TEXT,
        trg_tokens TSVECTOR
    )
    """
    )
INSERT_COMMAND = """INSERT INTO {} (src, trg) VALUES(%s, %s)"""

UPDATE_COMMAND = (
    """
    UPDATE {} as t
    SET src_tokens = to_tsvector('public.{}_nostop', t.src),
        trg_tokens = to_tsvector('public.{}_nostop', t.trg)
    """
    )

# Query to verify terminology
SQL = (
        """
        SELECT foo.id,
               ts_headline('public.{}_nostop',
                                foo.src_sent,
                                q_src,
                                'HighlightAll=TRUE'),
               ts_headline('public.{}_nostop',
                               foo.trg_sent,
                               q_trg,
                               'HighlightAll=TRUE'),
               foo.src_term,
               foo.trg_term
        FROM (SELECT bitext.id AS id,
                     bitext.src AS src_sent,
                     bitext.trg AS trg_sent,
                     q_src,
                     q_trg,
                     gloss.src AS src_term,
                     gloss.trg AS trg_term
              FROM bitext, gloss,
                   phraseto_tsquery('public.{}_nostop',
                                    replace(gloss.src, $$'$$, $$\'$$)
                                    ) q_src,
                   phraseto_tsquery('public.{}_nostop',
                                    replace(gloss.trg, $$'$$, $$\'$$)
                                    ) q_trg
              WHERE bitext.src_tokens @@ q_src AND
                    bitext.trg_tokens  @@ q_trg = {}
              ) AS foo
        ORDER BY id
        """)


def verify_terms(direction, bitext, glossary, successes=False):
    """Query the PostgreSQL database."""
    flag = 'FALSE'  # Search for errors in the use of terminology
    if successes:
        flag = 'TRUE'  # Search for successful application of terms

    if direction == 'eng-rus':
        src_lang, trg_lang = 'english', 'russian'
    elif direction == 'rus-eng':
        src_lang, trg_lang = 'russian', 'english'

    conn = None
    try:
        print('Connecting to the PostgreSQL database...')
        try:
            conn = psycopg2.connect(os.environ['DATABASE_URL'])
            local_db = False
        except KeyError:
            conn = psycopg2.connect(**config())
            local_db = True
        with conn:
            with conn.cursor() as cur:
                # Create bitext table
                table_name = 'bitext'
                for lang in (src_lang, trg_lang):
                    cur.execute("DROP TEXT SEARCH DICTIONARY IF EXISTS public.{}_nostop CASCADE".format(lang))
                    for command in CREATE_SEARCH_CONFIG:
                        cur.execute(command.format(lang, lang))
                if local_db:
                    cur.execute("DROP TEXT SEARCH DICTIONARY IF EXISTS public.my_synonym CASCADE".format(lang))
                    for command in ADD_RUS_SYNONYMS_CONFIG:
                        cur.execute(command)

                for command in CREATE_TAB_COMMANDS:
                    cur.execute(command.format(table_name))
                cur.executemany(INSERT_COMMAND.format(table_name), bitext)
                cur.execute(UPDATE_COMMAND.format(table_name, src_lang, trg_lang))

                # Create glossary table
                table_name = 'gloss'
                for command in CREATE_TAB_COMMANDS:
                    cur.execute(command.format(table_name))
                cur.executemany(INSERT_COMMAND.format(table_name), glossary)

                # Verify terminology
                cur.execute(SQL.format(src_lang, trg_lang,
                                       src_lang, trg_lang,
                                       flag))
                rows = cur.fetchall()

                for table in ('bitext', 'gloss'):
                    cur.execute("DROP TABLE IF EXISTS {}".format(table))
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
            print('Database connection closed.')
    return rows


if __name__ == '__main__':
    print(verify_terms('eng-rus', successes=False))
