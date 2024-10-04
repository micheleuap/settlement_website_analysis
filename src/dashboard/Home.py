import streamlit as st
import pandas as pd
from sqlalchemy import create_engine


engine = create_engine("sqlite:///data/data.db")
tables = ["documents", "cases", "notice_info", "expenses", "summaries"]
db = {table: pd.read_sql_table(table, engine) for table in tables}
cases = db["cases"].merge(db["notice_info"], "inner", on="case")
summ = db["summaries"].merge(db["documents"], "left", on=["case", "filename"])

colnames = {
    "allegations": "Allegations",
    "settlement_date": "Settlement Date",
    "settlement_amount": "Settlement Amount",
    "adps": "Average Distribution per Share ($)",
    "class_period": "Class Period",
    "attorney_fees": "Attorney Fees (% of Settlement)",
}

with open("src/dashboard/homepage_writeup.md", encoding="UTF-8") as f:
    markdown = "\n".join(f.readlines())

st.markdown(markdown)
