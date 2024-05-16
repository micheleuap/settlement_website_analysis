import pandas as pd
import fitz
from orm import documents_table, engine, notice_table
from sqlalchemy import select, insert
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import TokenTextSplitter
from typing import Optional
from langchain_community.vectorstores import FAISS
from assets import api_key


class LegalTeam(BaseModel):
    legal_team: Optional[str] = Field(
        default=None,
        description="The list of legal teams representing the class members",
    )


class ADPS(BaseModel):
    adps: Optional[float] = Field(
        default=None,
        description=(
            "The average distribution per damaged share in dollars before any tax deduction, costs, admin fees, etc."
            " If multiple shares exist please select the average distribution per common share"
        ),
    )


class AttorneyFees(BaseModel):
    attorney_fees: Optional[float] = Field(
        default=None,
        description=("Attorney Fees requested, as a percentage of the settlement fund"),
    )


class SecuritesIncluded(BaseModel):
    securities_included: Optional[str] = Field(
        default=None,
        description=(
            "The securities that are listed as included in "
            "the class and/or part of the plan of allocation."
        ),
    )


extract_info = {
    LegalTeam: "The name of the law firm representing the Class Members and Plaintiffs",
    ADPS: "The average settlement distribution per damaged share in dollars before any tax deduction, costs, admin fees, etc. (often found in the Class Recovery Statement)",
    AttorneyFees: "Attorney Fees requested by the legal counsel",
}


prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an expert extraction algorithm. "
            "Only extract relevant information from the following chunks of text. "
            "If you do not know the value of an attribute asked to extract, "
            "return null for the attribute's value.",
        ),
        ("human", "{text}"),
    ]
)


def join_output(docs):
    chunks = [
        f"\n\nCHUNK {i}\n" + doc.page_content for i, doc in enumerate(docs, start=1)
    ]
    return "".join(chunks)


text_splitter = TokenTextSplitter(chunk_size=100, chunk_overlap=50)
llm = ChatOpenAI(api_key=api_key, temperature=0)

with engine.connect() as conn:
    docs = conn.execute(
        select(documents_table).where(
            documents_table.c.title.contains("NOTICE OF"),
            documents_table.c.title.contains("PROPOSED SETTLEMENT"),
        )
    )
    docs = pd.DataFrame(docs.fetchall(), columns=docs.keys())
    docs["path"] = "../../data/legal_docs/" + docs.case + "/" + docs.filename + ".pdf"


for i, doc in docs.iterrows():
    f = fitz.open(doc.path)
    text = "".join([x.get_text() for x in f])
    chunks = text_splitter.split_text(text)
    vectorstore = FAISS.from_texts(
        chunks,
        embedding=OpenAIEmbeddings(api_key=api_key, model="text-embedding-3-small"),
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

    row = {"case": doc.case}
    for info, rag_prompt in extract_info.items():
        runnable = prompt | llm.with_structured_output(schema=info, include_raw=False)
        rag_extractor = {"text": retriever | join_output} | runnable
        output = rag_extractor.invoke(rag_prompt)
        row |= output
        print(doc.case, output)
    with engine.connect() as conn:
        _ = conn.execute(insert(notice_table).values(**row))
        _ = conn.commit()

with engine.connect() as conn:
    pd.read_sql_table("notice_info", conn)

with engine.connect() as conn:
    pd.read_sql_table("cases", conn).to_csv("../../cases.csv", index=False)
    pd.read_sql_table("documents", conn).to_csv("../../documents.csv", index=False)

notice_table.drop(engine)
print(join_output(retriever.invoke(rag_prompt)))
