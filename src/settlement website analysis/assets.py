import pandas as pd
import requests
from glob import glob

api_key = st.secrets["api-key"]
data_folder = "../../data/"
sites = pd.read_csv(data_folder + "Securities Settlement Websites.csv")


class RequestError(Exception):
    def __init__(self, *args: object, status_code, url) -> None:
        super().__init__(*args)
        self.status_code = status_code
        self.url = url


class Website:
    def __init__(self, url, name) -> None:
        self.url = url
        self.name = name
        self.home_page = None
        self.docs_page = None


def get(url):
    response = requests.get(url)
    if response.status_code != 200:
        raise RequestError(
            f"error {response.status_code}, page: {url}",
            status_code=response.status_code,
            url=url,
        )
    return response


def load_titles():
    titles = {}
    for file in glob("../../data/legal_docs/*/index.csv"):
        case = file.split("\\")[-2]
        with open(file) as f:
            df = pd.read_csv(f, encoding=f.encoding, index_col="filename")
        titles[case] = df
    df = pd.concat(titles, names=["case"]).reset_index()
    df.columns = df.columns.str.strip()
    return df


titles = load_titles()
