👋 Welcome to the securities litigation settlement dashboard!

I have scraped all legal filings from the settlement websites of a number of US securities litigation cases. 
This website uses LLMs/RAG to provide a simple overview of what happened in each case and filing

### Tab Overview 

##### 🔎 Settlement Overview 
For each settlement, this contains two tables:
- High level information about the case (what was the settlement amount, what were the allegations etc.)
- Legal fees filed by each law firm

##### 📃 Filing Summaries 
Contains chatgpt-generated summaries of each document filed in each case. 
If a given pdf file contains multiple sections, each section has its own summary.

##### 📊 Charts 
Contains charts that display trends across filings


### Methdodology
The RAG methodology is quite simple 
- embeddings are created for small blocks of text, for each document. Each case has its own little FAISS store (as no retrieval takes place across cases).
- For each document and information needed, text blocks are selected by cosine similarity with a (handwritten) query
- The blocks selected for that question are then concatenated, and text is extracted using the structured function calling functionality of chatgpt