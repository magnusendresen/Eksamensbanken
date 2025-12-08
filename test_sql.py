import sql_icp, os

mydb = sql_icp.DB("eksamensbanken", "postgres", os.getenv("pgsql_pw"))

mydb.add_subject("MAA1", "Matematikk 1T", "Matematikk", ["Algebra", "Funksjoner", "Geometri"])