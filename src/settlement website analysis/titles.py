import pandas as pd
import fitz
from glob import glob
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy import insert, select, delete
from orm import documents_table, engine
from assets import api_key

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """you extract the title of legal documents from the text provided, without rephrasing and without using any outside knowledge:

Example of titles include: 
 - "PROOF OF GENERAL CLAIM AND RELEASE"
 - "NOTICE OF MOTION AND MOTION FOR (1) FINAL APPROVAL OF CLASS ACTION SETTLEMENT AND APPROVAL OF PLAN OF ALLOCATION; AND (2) AN AWARD OF ATTORNEYS’ FEES AND EXPENSES AND AN AWARD TO PLAINTIFF PURSUANT TO 15 U.S.C. §78u-4(a)(4)"
 - "DECLARATION OF JOHN DOE REGARDING NOTICE DISSEMINATION, PUBLICATION, AND REQUESTS FOR EXCLUSION RECEIVED TO DATE"
 - "PLAINTIFF’S STATEMENT OF NON-OPPOSITION IN FURTHER SUPPORT OF MOTIONS FOR: (1) FINAL APPROVAL OF CLASS ACTION SETTLEMENT AND APPROVAL OF PLAN OF ALLOCATION; AND (2) AN AWARD OF ATTORNEYS’ FEES AND EXPENSES AND AN AWARD TO PLAINTIFF PURSUANT TO 15 U.S.C. §78u-4(a)(4)"
 - "MEMORANDUM OF LAW IN SUPPORT OF PLAINTIFF’S MOTION FOR FINAL APPROVAL OF CLASS ACTION SETTLEMENT AND APPROVAL OF PLAN OF ALLOCATION"
 - EXHIBIT X
 - ORDER APPROVING SETTLEMENT AND PROVIDING FOR NOTICE
 - STIPULATION AND AGREEMENT OF SETTLEMENT

If no title is provided, return "No title provided"
""",
        ),
        (
            "user",
            """please read the following page of legal document, and extract its title: 
            {page}""",
        ),
    ]
)

llm = ChatOpenAI(api_key=api_key)
files = list(
    filter(lambda x: x.endswith(".pdf"), glob("../../data/**", recursive=True))
)

chain = prompt | llm

# TODO skip files if empty

for f in files:
    with engine.connect() as conn:
        path = f.replace("\\", "/").split("/")
        filename = path[-1][:-4]
        case = path[-2]

        res = conn.execute(
            select(documents_table).where(
                documents_table.c.case == case, documents_table.c.filename == filename
            )
        )
        if res.all():
            continue

        try:
            p1 = fitz.open(f)[0].get_text()
            title = chain.invoke({"page", p1}).content
        except fitz.FileDataError as e:
            title = "No title provided"

        stmt = insert(documents_table).values(filename=filename, title=title, case=case)
        print(filename, case)
        print(title)
        result = conn.execute(stmt)
        conn.commit()


with engine.connect() as conn:
    t = pd.read_sql_table("documents", conn)
