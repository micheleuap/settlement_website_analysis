import pandas as pd
import requests
import os

api_key = os.getenv("openai_api")

data_folder = "data/"
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
