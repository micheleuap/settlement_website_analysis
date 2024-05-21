from glob import glob
import pandas as pd
from src.settlement_website_analysis.orm import engine, documents_table
from sqlalchemy import insert


def load_titles():
    titles = {
        file.split("\\")[-2]: pd.read_csv(file, index_col="filename")
        for file in glob("data/legal_docs/*/index.csv")
    }

    df = pd.concat(titles, names=["case"]).reset_index()
    df = df.rename(columns=lambda x: x.strip())
    df = df.rename(columns={"full_name": "title"})
    return df


with engine.connect() as conn:
    _ = conn.execute(insert(documents_table).values(load_titles().to_dict("records")))
    conn.commit()
