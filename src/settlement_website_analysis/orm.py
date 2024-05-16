from sqlalchemy import create_engine, Table, Column, String, Float, Integer, MetaData

engine = create_engine("sqlite:///data/data.db")

metadata_obj = MetaData()

documents_table = Table(
    "documents",
    metadata_obj,
    Column("title", String),
    Column("filename", String),
    Column("case", String),
)

case_table = Table(
    "cases",
    metadata_obj,
    Column("case", String),
    Column("website", String),
    Column("settlement_date", String),
    Column("settlement_amount", Integer),
    Column("class_period", String),
    Column("allegations", String),
)

notice_table = Table(
    "notice_info",
    metadata_obj,
    Column("case", String),
    Column("adps", Float),
    Column("legal_team", String),
    Column("attorney_fees", Float),
)

expenses_table = Table(
    "expenses",
    metadata_obj,
    Column("case", String),
    Column("filename", String),
    Column("page", Integer),
    Column("category", String),
    Column("amount", Float),
    Column("sub_amount", Float),
)


if __name__ == "__main__":
    metadata_obj.create_all(engine)
