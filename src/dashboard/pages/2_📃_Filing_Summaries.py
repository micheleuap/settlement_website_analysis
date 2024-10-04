import streamlit as st
from Home import summ, db


def row2para(row):
    title = row.title if row.sub_document == "main" else row.sub_document
    out = ""
    if row.sub_document == "main":
        out += f"🔗[**Link to the original document**]({row.link}) \n\n"
    else:
        out += f"**{title}**\n\n"

    summary = row.summary.replace("$", r"\$")
    if summary == "Not English":
        summary = "Pdf does not contain embedded text, or embedded text is corrupted"
    return out + summary


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


case_selected = st.selectbox(
    label="Select a settlement:", options=db["cases"].case, index=None
)

if case_selected:
    list_of_case_documents()
