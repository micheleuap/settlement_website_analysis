import streamlit as st
import altair as alt

from Home import cases, colnames

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


high_level_summary()