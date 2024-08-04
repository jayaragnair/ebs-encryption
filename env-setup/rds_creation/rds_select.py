from sqlalchemy import create_engine
from sqlalchemy import text
import pandas as pd
import sys


rds_endpoint = "database-1.cigs0yxxfgum.us-east-1.rds.amazonaws.com"

db_url = f"mysql+pymysql://sqlsqlsql:mysqlpassword@{rds_endpoint}:3306"
engine = create_engine(db_url)

with engine.connect() as connection:
    connection.execute()
    