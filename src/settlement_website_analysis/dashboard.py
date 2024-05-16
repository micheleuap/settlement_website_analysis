import streamlit as st
from orm import engine
import pandas as pd
import altair as alt

tab1, tab2 = st.tabs(["Case-Specific Info", "Overall Statistics"])
css = """
<style>
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
    font-size:1.2rem;
    }
</style>
"""

st.markdown(css, unsafe_allow_html=True)

tables = ["documents", "cases", "notice_info", "expenses"]
db = {table: pd.read_sql_table(table, engine) for table in tables}
cases = db["cases"].merge(db["notice_info"], "inner", on="case")

_, casebox, _ = tab1.columns([0.2, 0.6, 0.2])
casebox.write("##### Select a settlement")
case_selected = casebox.selectbox(
    label="", options=db["cases"].case, label_visibility="collapsed"
)

colnames = {
    "allegations": "Allegations",
    "settlement_date": "Settlement Date",
    "settlement_amount": "Settlement Amount",
    "adps": "Average Distribution per Share ($)",
    "class_period": "Class Period",
    "attorney_fees": "Attorney Fees (% of Settlement)",
}


tab1.write("## Settlement Information")
tab1.table(
    cases.set_index("case")
    .loc[
        case_selected,
        colnames.keys(),
    ]
    .rename(index=colnames)
)


tab1.write("## Expenses Filed by Attorneys")
expenses = (
    db["expenses"]
    .loc[lambda x: x.case == case_selected, ["category", "amount", "sub_amount"]]
    .rename(columns=lambda x: x.capitalize().replace("_", "-"))
)
breakdowns = expenses.Amount == 0
expenses.loc[breakdowns, "Category"] = "        " + expenses.loc[breakdowns, "Category"]
tab1.dataframe(expenses, hide_index=True, use_container_width=True)


tab2.write("### Relationship Between Attorney Fees and Settlement Amount")
tab2.altair_chart(
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
tab2.write("### Attorney Fees")
tab2.altair_chart(
    alt.Chart(att_fees)
    .mark_bar()
    .encode(
        x=alt.X("attorney_fees").title("Attorney Fees (binned)"),
        y=alt.Y("count").title("Count"),
    ),
    use_container_width=True,
)


tab2.write("### Distribution Per Share")
tab2.altair_chart(
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
