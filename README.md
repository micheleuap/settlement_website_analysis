# US Securities Litigation Dashboard

This project is a Streamlit dashboard designed to extract, process, and display key information from the settlement websites of US securities litigations. The tool automates the extraction of data from these websites, including parsing legal documents, and presents the findings in a user-friendly format.

### Link 
The streamlit dashboard is also hosted [here](https://ussettlementdashboard.streamlit.app/) on the streamlit community cloud. 

### Features

- **Web Scraping**: Extracts information directly from US securities litigation settlement websites.
- **Document Parsing**: Downloads and parses all legal proceeding PDFs stored on the websites.
- **Information Extraction**: Uses Retrieval-Augmented Generation (RAG) to analyze and locate specific information within the legal documents.
- **Data Population**: Automatically populates fields such as: Settlement Size, Allegations, Settlement Date, Plaintiffs and Defendants, and more
- **Filing summarization**: Summarizes each of the filed documents into a few paragraphs 
- **Streamlit Dashboard**: Displays all extracted information in an interactive dashboard for easy exploration and analysis.


### Requirements

- Python 3.x
- Langchain+OpenAI: To build the rag pipeline
- Streamlit: To build the dashboard.
- BeautifulSoup4: For web scraping.
- PyPDF2: For PDF parsing.
    
### Project Structure

```bash

📦us-securities-litigation-dashboard
 ┣ 📂data                          # Data storage (database and extracted and processed files)
 ┣ 📂src                           # Scripts for web scraping and document parsing
  ┣ 📂dashboard                    # Streamlit scripts
  ┗ 📂settlement-website-analyis   # scraping, parsing, RAG extraction
 ┣ 📜requirements.txt              # Python dependencies
 ┗ 📜README.md                     # Project documentation

```

### Future Enhancements

Add more advanced search and filtering capabilities.
Provide visual summaries of settlements and trends over time.
