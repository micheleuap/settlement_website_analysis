import pandas as pd
from assets import sites, data_folder, get, api_key
from glob import glob
from bs4 import BeautifulSoup
from typing import Optional
from sqlalchemy import insert, select, delete
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI
from orm import case_table, engine

root_dir = data_folder + "legal_docs/"
folders = glob("*", root_dir=root_dir)


class SettlementHomePage(BaseModel):
    """Information about a the settlement of a securities litigation"""

    settlement_date: str = Field(
        default=None, description="The date in which the settlement was stipulated"
    )
    settlement_amount: int = Field(
        default=None,
        description=("The dollar amount of the settlement pool"),
    )
    # settlement_shares: Optional[int] = Field(
    #     default=None,
    #     description=("The number of shares included as part of the settlement, if any"),
    # )
    class_period: str = Field(
        default=None,
        description=(
            "The class period for this settlement. This is the period within "
            "which a person must have traded to be a member of the class"
        ),
    )
    allegations: str = Field(
        default=None,
        description=(
            "The class action allegations. I.e. the company's "
            "misleading statements, or other fraudulent behavior"
        ),
    )


prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an expert extraction algorithm. "
            "Only extract relevant information from the text. "
            "If you do not know the value of an attribute asked to extract, "
            "return null for the attribute's value.",
        ),
        ("human", "{text}"),
    ]
)

llm = ChatOpenAI(api_key=api_key, temperature=0)

runnable = prompt | llm.with_structured_output(schema=SettlementHomePage)

for company in folders:
    with engine.connect() as conn:
        site = sites[sites.Company == company].squeeze().Website
        with open(f"{root_dir}{company}/home_page.html", encoding="utf-8") as f:
            soup = BeautifulSoup(f, features="html.parser")
        text = soup.find(class_="content_body").get_text()
        output = runnable.invoke(text)
        print(company, output)
        _ = conn.execute(
            insert(case_table).values(
                case=company,
                website=site,
                settlement_date=output.settlement_date,
                settlement_amount=output.settlement_amount,
                class_period=output.class_period,
                allegations=output.allegations,
            )
        )

        conn.commit()


t = pd.read_sql_table("cases", engine)

# with engine.connect() as conn:
#     conn.execute(delete(case_table))
#     conn.commit()
