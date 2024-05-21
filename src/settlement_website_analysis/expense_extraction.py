import base64
from typing import Optional

import fitz
import pandas as pd
from joblib import Parallel, delayed
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI
from numpy import nan
from sqlalchemy import insert

from src.settlement_website_analysis.assets import api_key, data_folder
from src.settlement_website_analysis.orm import engine, expenses_table


class ExpenseRow(BaseModel):
    CATEGORY: str = Field(
        default=None,
        description="The descriptions of the expense, including potentially its total",
    )
    AMOUNT: float = Field(
        default=None,
        description="The amount of the expense",
    )
    SUB_AMOUNT: Optional[float] = Field(
        default=None,
        description="This is used to provide the breakdown of other amounts in the table (in the amounts column)",
    )


class ExpenseTable(BaseModel):
    rows: list[ExpenseRow] = Field(
        default=None,
        description="The list of rows contained in the table, including the total row at the bottom if present",
    )


class InvalidTableFormat(Exception):
    pass


def extract_tables(case, filename):
    path = f"{data_folder}legal_docs/{case}/{filename}.pdf"
    try:
        file = fitz.open(path)
    except (fitz.FileDataError, fitz.FileNotFoundError):
        return None

    tables = []
    for page_num, page in enumerate(file):
        ts = []
        for table in page.find_tables():
            df = table.to_pandas()
            if (
                "AMOUNT" in df.columns
                and not df.columns.isin(["NARRATIVE", "HOURS"]).any()
            ):
                ts.append(table)

        if ts:
            tbls = []
            for table in ts:
                try:
                    tbls.append(manual_table(table.to_pandas()))
                except (InvalidTableFormat, ValueError):
                    tbls.append(llm_table(page, table))
            table = pd.concat(tbls)
            tables.append((page_num, page.get_text(), table))

    return tables


def manual_table(df):
    df = df.copy()
    if len(df.columns) == 3:
        if not all(df.columns == ["CATEGORY", "Col1", "AMOUNT"]):
            print(df)
            raise InvalidTableFormat
        df.rename(columns={"Col1": "SUB_AMOUNT"}, inplace=True)
    elif len(df.columns) == 2:
        if not (
            all(df.columns == ["CATEGORY", "AMOUNT"])
            or all(df.columns == ["EXPENSE", "AMOUNT"])
        ):
            print(df)
            raise InvalidTableFormat
        df["SUB_AMOUNT"] = ""
        df = df.rename(columns={"EXPENSE": "CATEGORY"})
    else:
        print(df)
        raise InvalidTableFormat

    df[["AMOUNT", "SUB_AMOUNT"]] = df[["AMOUNT", "SUB_AMOUNT"]].apply(
        lambda x: x.str.replace("[$ ,]{1,}", "", regex=True)
        .replace("", nan)
        .fillna(0)
        .astype("float")
    )
    return df


def llm_table(page, table):
    model = ChatOpenAI(model="gpt-4o", api_key=api_key)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "Output the content of the table provided in the image"),
            (
                "user",
                [
                    {
                        "type": "image_url",
                        "image_url": "data:image/jpeg;base64,{image_data}",
                    }
                ],
            ),
        ]
    )
    chain = prompt | model.with_structured_output(
        schema=ExpenseTable, include_raw=False
    )
    image_data = base64.b64encode(
        page.get_pixmap(clip=table.bbox, dpi=120).tobytes()
    ).decode("utf-8")
    out = chain.invoke(image_data)
    return pd.DataFrame(out.dict()["rows"])


expense_docs = pd.read_sql_table("documents", engine)[
    lambda x: x.title.str.contains("Expense")
    & (~x.case.isin(pd.read_sql_table("expenses", engine).case))
]

out = Parallel(-1, verbose=20)(
    delayed(extract_tables)(doc.case, doc.filename)
    for i, doc in expense_docs.iterrows()
)

extr = {}
for case, fname, doc in zip(expense_docs.case, expense_docs.filename, out):
    if doc:
        for page in doc:
            extr[case, fname, page[0]] = page[-1]

df = (
    pd.concat(
        {k: v for k, v in extr.items()}, names=["case", "filename", "page", "idx"]
    )
    .droplevel("idx")
    .replace("", nan)
    .dropna(how="all")
)

assert (
    df.groupby(df.index)
    .CATEGORY.agg(lambda x: ((x.str.contains("TOTAL") == True) + x.isna()).sum())
    .all()
)

is_total = (df.CATEGORY.str.contains("TOTAL") == True) + df.CATEGORY.isna()
df.loc[is_total, "CATEGORY"] = "TOTAL"

tx = df[df.CATEGORY != "TOTAL"]


tx = tx.reset_index().rename(columns=lambda x: x.lower())
with engine.connect() as conn:
    conn.execute(insert(expenses_table).values(tx.to_dict("records")))
    conn.commit()
