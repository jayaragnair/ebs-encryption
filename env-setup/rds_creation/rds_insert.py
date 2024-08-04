from sqlalchemy import create_engine
from sqlalchemy import text
import pandas as pd
import sys

df = pd.read_csv("income.csv")
db_url = sys.argv[1]
# db_url = f"mysql+pymysql://sqlsqlsql:mysqlpassword@database-1.cigs0yxxfgum.us-east-1.rds.amazonaws.com:3306"
engine = create_engine(db_url)


with engine.connect() as connection:
    connection.execute(statement=text("CREATE DATABASE IF NOT EXISTS income"))
    connection.execute(statement=text("USE income"))

    df.to_sql(
        name="income",
        if_exists="replace",
        con=f"{db_url}/income"
    )
    connection.commit()
    response = connection.execute(statement=text("SELECT * FROM income"))
    print(response.fetchall())
