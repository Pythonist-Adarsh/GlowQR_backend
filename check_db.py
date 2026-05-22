import os
import sqlalchemy
from database import engine

with engine.connect() as conn:
    res = conn.execute(sqlalchemy.text("SELECT column_name FROM information_schema.columns WHERE table_name='users'"))
    columns = [row[0] for row in res]
    print('Users columns:', columns)

    res2 = conn.execute(sqlalchemy.text("SELECT column_name FROM information_schema.columns WHERE table_name='businesses'"))
    columns2 = [row[0] for row in res2]
    print('Businesses columns:', columns2)
