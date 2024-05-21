from glob import glob
import pandas as pd
from src.settlement_website_analysis.orm import engine, documents_table
from sqlalchemy import insert


def load_titles():
    titles = {}
    for file in glob("data/legal_docs/*/index.csv"):
        case = file.split("\\")[-2]
        with open(file) as f:
            df = pd.read_csv(f, encoding=f.encoding, index_col="filename")
        titles[case] = df
    df = pd.concat(titles, names=["case"]).reset_index()
    df = df.rename(columns=lambda x: x.strip())
    df = df.rename(columns={"full_name": "title"})
    return df


with engine.connect() as conn:
    conn.execute(insert(documents_table).values(load_titles().to_dict("records")))
    conn.commit()
