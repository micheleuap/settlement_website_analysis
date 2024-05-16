import pandas as pd
import fitz
from orm import expenses_table, engine
from assets import api_key, titles
from joblib import Parallel, delayed
from numpy import nan
from sqlalchemy import insert


def extract_tables(case, filename):
    path = f"../../data/legal_docs/{case}/{filename}.pdf"
    try:
        file = fitz.open(path)
    except fitz.FileDataError:
        return None

    tables = []
    for page_num, page in enumerate(file):
        ts = []
        for table in page.find_tables():
            df = table.to_pandas()
            if "AMOUNT" in df.columns and "NARRATIVE" not in df.columns:
                ts.append(df)
                page.add_redact_annot(table.bbox)
        if ts:
            page.apply_redactions()
            tables.append((page_num, page.get_text(), ts))
            return tables


expense_docs = titles[titles.full_name.str.contains("Expense")]
out = Parallel(-1, verbose=20)(
    delayed(extract_tables)(doc.case, doc.filename)
    for i, doc in expense_docs.iterrows()
)

extr = {}
for case, fname, doc in zip(expense_docs.case, expense_docs.filename, out):
    if doc:
        for page in doc:
            extr[case, fname, page[0]] = page[1:]

assert not [k for k in extr if len(extr[k][1]) != 1]

for x in extr:
    df = extr[x][1][0]
    if len(df.columns) == 3:
        assert all(df.columns == ["CATEGORY", "Col1", "AMOUNT"])
        df.rename(columns={"Col1": "SUB_AMOUNT"}, inplace=True)
    if len(df.columns) == 2:
        assert all(df.columns == ["CATEGORY", "AMOUNT"])

df = (
    pd.concat(
        {k: v[1][0] for k, v in extr.items()}, names=["case", "filename", "page", "idx"]
    )
    .droplevel("idx")
    .replace("", nan)
    .dropna(how="all")
)

df[["AMOUNT", "SUB_AMOUNT"]] = df[["AMOUNT", "SUB_AMOUNT"]].apply(
    lambda x: x.str.replace("[$ ,]", "", regex=True).fillna(0).astype("float")
)


assert (
    df.groupby(df.index)
    .CATEGORY.agg(lambda x: ((x.str.contains("TOTAL") == True) + x.isna()).sum())
    .all()
)

is_total = (df.CATEGORY.str.contains("TOTAL") == True) + df.CATEGORY.isna()
df.loc[is_total, "CATEGORY"] = "TOTAL"

tx = df[df.CATEGORY != "TOTAL"]
sums = tx.groupby(df.index.names).AMOUNT.sum()
assert ((df[df.CATEGORY == "TOTAL"].AMOUNT - sums).abs() <= 0.01).all()
tx = tx.reset_index().rename(columns=lambda x: x.lower())


with engine.connect() as conn:
    conn.execute(insert(expenses_table).values(tx.to_dict("records")))
    conn.commit()
