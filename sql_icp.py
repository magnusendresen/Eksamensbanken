import psycopg2
from psycopg2 import sql

class DB:
    def __init__(self, dbname, user, password, host='localhost', port=5432):
        self.connection = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        self.connection.autocommit = True

    def query(self, query, params=None):
        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            if query.strip().upper().startswith("SELECT"):
                return cursor.fetchall()
            
    def add_subject(self, code: str, name: str = None, domain: str = None, topics: list[str] = None):
        code = code.upper()
        name = smart_cap(name) 
        domain = smart_cap(domain)
        topics = [smart_cap(t) for t in topics] if topics else []
        self.query(
            """
            INSERT INTO subjects(code, name, domain, topics)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (code) DO NOTHING
            """,
            (code, name, domain, topics)
        )

def smart_cap(s: str) -> str:
    words = s.split()
    out = []
    for w in words:
        if len(w) > 3:
            out.append(w.capitalize())
        else:
            out.append(w.lower())
    return " ".join(out)

