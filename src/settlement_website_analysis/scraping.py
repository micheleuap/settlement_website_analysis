import pandas as pd
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin
from shutil import rmtree
from random import shuffle
from src.settlement_website_analysis.assets import sites, RequestError, get, Website


def epiq(site):
    current_page = urljoin(site.url, "Home/Documents")
    response = get(current_page)
    soup = BeautifulSoup(response.text)
    docs = soup.find(id="Documents")
    folder = "data/legal_docs/" + site.name
    if os.path.exists(folder):
        return
    os.mkdir(folder)
    try:
        save_all(docs, folder, site)
    except RequestError as e:
        with open(folder + "/" + "failed.txt", "a") as f:
            f.write(f"{e.status_code},{e.url}\n")
        print(f"{e.status_code}: {e.url}")
    except:
        rmtree(folder)


def gilardi(site):
    gilardi_page(site)
    gilardi_docs(site)


def gilardi_docs(site):
    folder = "data/legal_docs/" + site.name

    with open(f"{folder}/docs_page.html", "rt", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read())

    links = soup.find(class_="table_legalRights").find_all("a")
    links = list(enumerate(links, start=1))

    df = pd.DataFrame(
        [
            {
                "filename": i,
                "full_name": item.text,
                "link": urljoin(site.url, item.get("href")),
            }
            for i, item in links
        ]
    )

    df.to_csv(f"{folder}/index.csv", index=False, encoding="utf-8")

    for i, row in df.iterrows():
        path = f"{folder}/{row.filename}.pdf"
        if not os.path.exists(path):
            try:
                response = get(row.link)
                with open(path, "wb") as file:
                    file.write(response.content)
            except RequestError as e:
                print(e)


def maybe_write(path, text):
    if not os.path.exists(path):
        with open(path, "wt", encoding="utf-8") as f:
            f.write(text)


def gilardi_page(site):
    folder = "data/legal_docs/" + site.name

    current_page = urljoin(site.url, "case-documents.aspx")
    response = get(current_page)
    site.docs_page = response.text

    if not os.path.exists(folder):
        os.mkdir(folder)
    maybe_write(f"{folder}/home_page.html", site.home_page)
    maybe_write(f"{folder}/docs_page.html", site.docs_page)


def save_all(docs, folder, site, prefix="", data=None):
    if not data:
        data = []
    lvl = list(enumerate(docs.ul.find_all("li", recursive=False), start=1))
    shuffle(lvl)
    for counter, item in lvl:
        response = get(urljoin(site.url, item.a.get("href")))
        fname = f"{prefix}{counter}."
        path = f"{folder}/{fname}.pdf"
        with open(path, "wb") as file:
            file.write(response.content)

        if item.ul is not None:
            save_all(item, folder, site, prefix=fname, data=data)
        data.append({"filename": fname, "full_name": item.a.text})
    pd.DataFrame(data).to_csv(f"{folder}/index.csv", index=False)


for idx, site in sites[sites.Company == "Airbus"].iterrows():
    site = Website(site.Website, site.Company)

    try:
        response = get(site.url)
    except:
        print(site.url)
        continue
    site.home_page = response.text

    if "www.gilardi.com" in response.text:
        gilardi(site)
        print(site.name)
