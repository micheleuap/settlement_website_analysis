import streamlit as st
import altair as alt
import pandas as pd
from sqlalchemy import create_engine


def row2para(row):
    title = row.title if row.sub_document == "main" else row.sub_document

    t = (
        f"🔗[**Link to the original document**]({row.link}) \n\n"
        if row.sub_document == "main"
        else f"**{title}**\n\n"
    ) + row.summary.replace("$", r"\$")
    return t


def high_level_summary():
    st.write("### Relationship Between Attorney Fees and Settlement Amount")
    st.altair_chart(
        alt.Chart(
            cases.set_index("case")[["attorney_fees", "settlement_amount"]].rename(
                columns=colnames
            )
        )
        .encode(
            x=alt.X("Settlement Amount").scale(type="log", base=10),
            y="Attorney Fees (% of Settlement)",
        )
        .mark_point(filled=True, size=100, opacity=0.8)
        .configure_axisX(grid=False)
        .interactive(),
        use_container_width=True,
    )

    att_fees = cases["attorney_fees"].round().astype(int).value_counts()
    att_fees = (
        att_fees.reindex(range(att_fees.index.min(), att_fees.index.max() + 1))
        .fillna(0)
        .reset_index()
    )
    att_fees.attorney_fees = att_fees.attorney_fees.astype(str)
    st.write("### Attorney Fees")
    st.altair_chart(
        alt.Chart(att_fees)
        .mark_bar()
        .encode(
            x=alt.X("attorney_fees").title("Attorney Fees (binned)"),
            y=alt.Y("count").title("Count"),
        ),
        use_container_width=True,
    )

    st.write("### Distribution Per Share")
    st.altair_chart(
        alt.Chart(cases.rename(columns=colnames))
        .mark_bar()
        .encode(
            alt.X(
                "Average Distribution per Share ($)",
                bin={"maxbins": 25},
                type="quantitative",
            ),
            y="count()",
        )
        .interactive(),
        use_container_width=True,
    )


def settlement_overview():
    st.write("## Settlement Information")
    st.table(
        cases.set_index("case")
        .loc[
            case_selected,
            colnames.keys(),
        ]
        .rename(index=colnames)
    )

    st.write("## Expenses Filed by Attorneys")
    expenses = (
        db["expenses"]
        .loc[
            lambda x: x.case == case_selected,
            ["category", "amount", "sub_amount"],
        ]
        .rename(columns=lambda x: x.capitalize().replace("_", "-"))
    )
    breakdowns = expenses.Amount == 0
    expenses.loc[breakdowns, "Category"] = (
        "        " + expenses.loc[breakdowns, "Category"]
    )
    st.dataframe(expenses, hide_index=True, use_container_width=True)


def list_of_case_documents():
    if case_selected:
        st.header("List of Case Documents")
        main = summ[lambda x: (x.case == case_selected) & (x.sub_document == "main")]
        st.markdown(
            main.apply(lambda x: f" - [{x.title}](#{x.filename})", axis=1).str.cat(
                sep="\n"
            ),
        )
        st.header("Document Summaries")

        for i, row in main.iterrows():
            st.subheader(row.title, anchor=row.filename)
            st.markdown(
                summ[(summ.case == case_selected) & (summ.filename == row.filename)]
                .apply(row2para, axis=1)
                .str.cat(sep="\n\n")
            )


css = """
<style>
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
    font-size:1.1rem;
    }
</style>
"""

st.markdown(css, unsafe_allow_html=True)

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


t1, t2 = st.tabs(["Settlement Analysis", "General Overview"])
with t2:
    high_level_summary()
with t1:
    case_selected = st.selectbox(
        label="Select a settlement:", options=db["cases"].case, index=None
    )
    if case_selected:
        c1, c2 = st.tabs(["Settlement Overview", "Summary of Court Documents"])
        with c1:
            settlement_overview()
        with c2:
            list_of_case_documents()
