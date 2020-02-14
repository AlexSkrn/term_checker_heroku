#!/usr/bin/env python3
import os
import psycopg2
from config import config


def bitext_sql(sql):
    """Use for test-querying the database."""
    conn = None
    try:
        print('Connecting to the PostgreSQL database...')
        try:
            conn = psycopg2.connect(os.environ['DATABASE_URL'])
        except KeyError:
            conn = psycopg2.connect(**config())
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                row = cur.fetchone()
                while row is not None:
                    print(row)
                    row = cur.fetchone()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
            print('Database connection closed.')


def verify_terms(direction, successes=False):
    """Query the PostgreSQL database."""
    flag = 'FALSE'  # Search for errors in the use of terminology
    if successes:
        flag = 'TRUE'  # Search for successful application of terms

    if direction == 'eng-rus':
        src_lang, trg_lang = 'english', 'russian'
    elif direction == 'rus-eng':
        src_lang, trg_lang = 'russian', 'english'

    sql = (
            """
            SELECT id,
                   ts_headline('public.{}_nostop',
                                    src,
                                    q_src,
                                    'HighlightAll=TRUE'),
                   ts_headline('public.{}_nostop',
                                   trg,
                                   q_trg,
                                   'HighlightAll=TRUE'),
                   src_term,
                   trg_term
            FROM (SELECT id, src, trg, q_src, q_trg, src_term, trg_term
                  FROM bitext, gloss,
                       phraseto_tsquery('public.{}_nostop',
                                        replace(src_term, $$'$$, $$\'$$)
                                        ) q_src,
                       phraseto_tsquery('public.{}_nostop',
                                        replace(trg_term, $$'$$, $$\'$$)
                                        ) q_trg
                  WHERE src_tokens @@ q_src AND
                        trg_tokens  @@ q_trg = {}
                  ) AS foo
            ORDER BY id
            """)
    conn = None
    try:
        print('Connecting to the PostgreSQL database...')
        try:
            conn = psycopg2.connect(os.environ['DATABASE_URL'])
        except KeyError:
            conn = psycopg2.connect(**config())
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql.format(src_lang, trg_lang,
                                       src_lang, trg_lang,
                                       flag))
                rows = cur.fetchall()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
            print('Database connection closed.')
    return rows


if __name__ == '__main__':
    print(verify_terms('eng-rus', successes=False))
