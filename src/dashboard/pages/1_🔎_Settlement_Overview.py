import streamlit as st
from Home import cases, db, colnames


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


case_selected = st.selectbox(
    label="Select a settlement:", options=db["cases"].case, index=None
)

if case_selected:
    settlement_overview()
