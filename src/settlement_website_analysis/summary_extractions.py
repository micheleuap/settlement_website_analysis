import re
from pprint import pprint
from typing import Dict, List

import fitz
import nltk
import pandas as pd
import spacy
from langchain_community.document_transformers.embeddings_redundant_filter import (
    EmbeddingsClusteringFilter,
)
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from nltk.corpus import words
from sqlalchemy import insert, select

from src.settlement_website_analysis.assets import api_key, data_folder
from src.settlement_website_analysis.orm import engine, summaries_table


# A class representing the document summary structure
class DocumentSummary(BaseModel):
    content: str = Field(
        default=None,
        description="A bullet point list of what information can be found in the document",
    )
    summary: str = Field(
        default=None,
        description="Key takeaways from the document",
    )


# A class to recognize English language text using NLTK
class EnglishRecognizer:
    def __init__(self) -> None:
        nltk.download("words", quiet=True)
        nltk.download("punkt", quiet=True)
        self.word_list = set(words.words())

    def is_english(self, text: str, threshold: float = 0.5) -> bool:
        """
        Check if the given text is predominantly in English.

        Parameters:
        - text (str): The input text to evaluate.
        - threshold (float): The minimum fraction of words that must be English.

        Returns:
        - bool: True if the text is mostly in English, False otherwise.
        """
        tokens = nltk.word_tokenize(text)
        if len(tokens) == 0:
            return False
        english_words = [word for word in tokens if word.lower() in self.word_list]
        return len(english_words) / len(tokens) > threshold


def further_split(sent: str, maxlen: int) -> List[str]:
    """
    Chunk long strings where no sentence boundaries are identified.

    Parameters:
    - sent (str): The input sentence to split.
    - maxlen (int): Maximum allowed chunk length.

    Returns:
    - List[str]: A list of sentence chunks.
    """
    if len(sent) < maxlen:
        return [sent]

    sents = re.split(r"(\s{1,}|\n)", sent)
    if all([len(x) < maxlen for x in sents]):
        return sents

    return [sent[i : i + maxlen] for i in range(0, len(sent), maxlen)]


def make_chunks(t: str, nlp: spacy.Language, maxlen: int = 1000) -> List[str]:
    """
    Splits a large text into manageable chunks based on sentence boundaries.

    Parameters:
    - t (str): The input text.
    - nlp: A SpaCy language model instance.
    - maxlen (int): The maximum length of each chunk.

    Returns:
    - List[str]: List of chunks.
    """
    chunks = [""]
    for sent in nlp(t).sents:
        for subsent in further_split(sent.text, maxlen):
            if len(chunks[-1] + subsent) < maxlen:
                chunks[-1] += subsent
            else:
                chunks.append(subsent)

    return chunks


def split_docs(file: fitz.Document) -> List[str]:
    """
    Splits a PDF document into smaller sub-documents based on some heuristic.

    Parameters:
    - file: A PyMuPDF file object.

    Returns:
    - List[str]: List of sub-document text chunks.
    """
    sections = [""]
    titles = ["main"]
    for page in f:
        t = (
            page.get_text(clip=fitz.Rect(0, 40, f[0].rect[-2], 734))
            .replace("\n", " ")
            .strip()
            .replace("  ", " ")
        )
        if re.match(r"^EXHIBIT [^\s]{1,3}$", t):
            sections.append("")
            titles.append(t)
        else:
            sections[-1] += r"\n" + t

    return dict(zip(titles, sections))


def extract_summaries(subdocuments: List[str]) -> Dict[str, str]:
    """
    Generate summaries for a list of subdocuments using an LLM model.

    Parameters:
    - subdocs (List[str]): List of text chunks (sub-documents).

    Returns:
    - Dict[str, str]: A dictionary mapping sub-document titles to their summaries.
    """
    prompt1 = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are the greatest legal document summarizer in the world.\n"
                "You summarize legal documents for the general public impacted by class actions",
            ),
            (
                "human",
                "Please summarize the following legal document from the settlement against AAC. First outline the content of the document then, if relevant report any key figures or facts. "
                "Please focus on information specific to this document, as opposed to information that is general to the whole lawsuit"
                "\n---\n\n{text}",
            ),
        ]
    )

    prompt2 = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are the greatest legal document summarizer in the world.\n"
                "You are provided chunks of a given legal document (separated by three dashes ---) "
                "and provide summaries for the general public impacted by class actions",
            ),
            (
                "human",
                "Please summarize the following text from the settlement against AAC. First outline the content of the document then, if relevant report any key figures or facts. "
                "Please focus on information specific to this document, as opposed to information that is general to the whole lawsuit"
                "\n---\n\n{text}",
            ),
        ]
    )

    model1 = prompt1 | llm
    model2 = prompt2 | llm

    document_summaries = {}
    for title, subdoc in subdocuments.items():
        if not english_recog.is_english(subdoc, threshold=0.05):
            summary = "Not English"
        elif len(subdoc) <= 10000:
            summary = model1.invoke(subdoc).content
        else:
            docs = [
                Document(chunk, chunk_n=i)
                for i, chunk in enumerate(make_chunks(subdoc, nlp=nlp))
            ]
            summ_text = fltr.transform_documents(docs)
            summ_text = [chunk.to_document().page_content for chunk in summ_text]
            summ_text = "\n\n----\n".join(summ_text)
            summary = model2.invoke(summ_text).content

        document_summaries[title] = summary
    return document_summaries


dry_run = False
nlp = spacy.load("en_core_web_sm")
docs = pd.read_sql_table("documents", engine)
llm = ChatOpenAI(api_key=api_key)
embedder = OpenAIEmbeddings(model="text-embedding-3-small", api_key=api_key)
fltr = EmbeddingsClusteringFilter(embeddings=embedder, num_clusters=8, sorted=True)
english_recog = EnglishRecognizer()

for _, row in docs.iterrows():
    if not dry_run:
        with engine.connect() as conn:
            if conn.execute(
                select(summaries_table).where(
                    summaries_table.c.case == row.case,
                    summaries_table.c.filename == row.filename,
                )
            ).all():
                continue

    print(f"{row.case} {row.filename}")
    path = f"data/legal_docs/{row.case}/{row.filename}.pdf"
    try:
        with fitz.open(path) as f:
            subdocs = split_docs(f)
    except Exception:
        print("Failed " + "-" * 80)
        continue

    summaries = extract_summaries(subdocs)
    values = [
        {
            "sub_document": sub_document,
            "summary": summary,
            "filename": row.filename,
            "case": row.case,
        }
        for sub_document, summary in summaries.items()
    ]
    if dry_run:
        pprint(values)
    else:
        with engine.connect() as conn:
            _ = conn.execute(insert(summaries_table).values(values))
            conn.commit()

# from sqlalchemy import delete

# with engine.connect() as conn:
#     _ = conn.execute(delete(summaries_table))
#     conn.commit()

pd.read_sql_table("summaries", engine)
