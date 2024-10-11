import base64
from typing import Optional, List, Tuple

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


def extract_tables(case: str, filename: str) -> List[Tuple[int, str, pd.DataFrame]]:
    """
    Extracts relevant tables from a PDF document based on specific column criteria and processes them.

    Parameters:
    -----------
    case : str
        The name or identifier of the legal case. Used to build the path to the PDF file.
    filename : str
        The name of the PDF file (without the extension) from which tables are extracted.

    Returns:
    --------
    List[Tuple[int, str, pd.DataFrame]] or None
        A list of tuples, where each tuple contains:
        - `page_num` (int): The page number where the table was found.
        - `page_text` (str): The text content of the page where the table was found.
        - `table` (pd.DataFrame): The extracted and processed table in the form of a Pandas DataFrame.

        If the PDF file is not found or cannot be opened, the function returns `None`.

    Raises:
    -------
    fitz.FileDataError
        If there is an issue with reading the PDF file data.
    fitz.FileNotFoundError
        If the file specified by `path` does not exist.

    Notes:
    ------
    - The function looks for tables that contain the column "AMOUNT" and exclude the columns "NARRATIVE" and "HOURS".
    - It uses manual processing (`manual_table`) for valid table formats or a language model (`llm_table`) for fallback in case of invalid formats.
    - Multiple tables on the same page are concatenated into one DataFrame before appending them to the result list.

    Example:
    --------
    >>> extract_tables("case_123", "document")
    [(1, "Page 1 text content", DataFrame), (2, "Page 2 text content", DataFrame)]
    """

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
    """
    Parameters:
    -----------
    df : pd.DataFrame
        A DataFrame containing financial or categorical data that needs to be processed.
        The DataFrame is expected to have either two or three columns:
        - ["CATEGORY", "AMOUNT"]
        - ["EXPENSE", "AMOUNT"]
        - ["CATEGORY", "Col1", "AMOUNT"]

    Returns:
    --------
    pd.DataFrame
        The processed DataFrame with updated column names and cleaned numeric values in
        the 'AMOUNT' and 'SUB_AMOUNT' columns.
    """
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
