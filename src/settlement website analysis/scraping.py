import pandas as pd
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin
from shutil import rmtree
from random import shuffle
from assets import sites, RequestError, get, Website
from glob import glob

# with open("src/settlement website analysis/headers.yaml") as f:
#     headers = yaml.safe_load(f)
# headers = {str(k):str(v) for k, v in headers.items()}


# from zenrows import ZenRowsClient
# client = ZenRowsClient("6a819a136ba4f0c77b45a8361ce9ee5c2509a268")


def epiq(site):
    ## the try except should go in the save all, so that it continues even if it fails one. 
    ##  the 
    current_page = urljoin(site.url, "Home/Documents")
    response = get(current_page)    
    soup = BeautifulSoup(response.text)
    docs = soup.find(id="Documents")
    folder = "../../data/legal_docs/" + site.name
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
    folder = "../../data/legal_docs/" + site.name

    current_page = urljoin(site.url, "case-documents.aspx")
    response = get(current_page)    
    site.docs_page = response.text
    with open(f"{folder}/home_page.html", "wt", encoding="utf-8") as f:
        f.write(site.home_page)
    with open(f"{folder}/docs_page.html", "wt", encoding="utf-8") as f:
        f.write(site.docs_page)
    
    if os.path.exists(folder):
        return

    soup = BeautifulSoup(response.text)    
    os.mkdir(folder)

    links = soup.find(class_="table_legalRights").find_all("a")
    links = list(enumerate(links, start=1))
    with open(f"{folder}/index.csv", "wt") as f:
        f.write("filename, full_name\n")
    
    for i, item in links:
        response = get(urljoin(site.url, item.get("href")))
        fname = f"{i}"
        path = f"{folder}/{fname}.pdf"
        with open(path, "wb") as file:
            file.write(response.content)
        with open(f"{folder}/index.csv", "a") as f:
            f.write(f"{fname},{item.text.replace(",", "")}\n")

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
        
        if item.ul is not  None:
            save_all(item, folder, site, 
                     prefix=fname, 
                     data=data)
        data.append({"filename": fname, 
                     "full_name": item.a.text})
    pd.DataFrame(data).to_csv(f"{folder}/index.csv", index=False)

for idx, site in sites.iterrows():
    site = Website(site.Website, site.Company)
    if site.name not in glob("*", root_dir="../../data/legal_docs/"): continue # TODO remove

    try:
        response = get(site.url)    
    except:
        print(site.url)
        continue
    site.home_page = response.text

    if "epiqglobal.com" in response.text:
        continue
        epiq(site)

    if "www.gilardi.com" in response.text:
        gilardi(site)


# SQM is a missing gilardi???
