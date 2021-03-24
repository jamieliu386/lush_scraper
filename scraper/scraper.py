from bs4 import BeautifulSoup
import hashlib
import json
import os
import requests
from typing import List, Tuple

cache_path = "cached_pages"

if not os.path.isdir(cache_path):
    os.mkdir(cache_path)

class Price:
    def __init__(self, size, unit, price) -> None:
        self.size = size
        self.unit = unit
        self.price = price

class Product:
    def __init__(self) -> None:
        self.name = None
        self.type = None
        self.top_description = None
        self.prices = []
        self.description = None
        self.benefits = []
        self.scent = []
        self.usage = None
        self.ingredients = []

class GiftProduct:
    def __init__(self) -> None:
        self.name = None
        self.type = None
        self.size = None
        self.unit = None

class GiftSet:
    def __init__(self) -> None:
        self.name = None
        self.type = None
        self.top_description = None
        self.prices = []
        self.included = []

def split_unit(s: str) -> Tuple[float, str]:
    for i,c in enumerate(s):
        if not c.isdigit() and not c == ".":
            break
    return float(s[:i]), s[i:].strip()

def get_name(soup) -> str:
    return soup.find("h1").string.strip()

def get_product_type(soup) -> str:
    return soup.find("div", {"class": "tagline"}).string.strip()

def get_top_description(soup) -> str:
    desc = soup.find("div", {"class": "top-description"})
    if desc is None or desc.string is None:
        return ""
    return desc.string.strip()

def get_prices(soup) -> List[Price]:
    name_price = soup.find_all("span", {"class": "name-price"})
    result = []
    for np in name_price:
        size = np.find("span", {"class": "name"}).string
        size, unit = split_unit(size)
        if unit == "":
            unit = "oz."
        price = float(np.find("span", {"class": "value text-nowrap"})["content"])
        result.append(Price(size, unit, price))
    return result

def get_description(soup) -> str:
    desc_tab = soup.find("div", {"id": "tab-description"})
    if desc_tab is None or desc_tab.find("p") is None:
        return ""
    return desc_tab.find("p").contents[0].strip()

def get_benefits(soup) -> List[str]:
    desc_tab = soup.find("div", {"id": "tab-description"})
    benefits = desc_tab.find_all("li")
    return [b.string.strip() for b in benefits]

def get_scent(soup) -> List[str]:
    desc_tab = soup.find("div", {"id": "tab-description"})
    scents = desc_tab.find("div", {"class": "mt-1"})
    return [] if scents is None else [s.strip() for s in scents.string.split('|')]

def get_usage(soup) -> str:
    tab = soup.find("div", {"id": "tab-how-to-use"})
    if tab is None or tab.find("p") is None:
        return ""
    return tab.find("p").string.strip()

def get_ingredients(soup) -> List[str]:
    tab = soup.find("div", {"id": "tab-ingredients"})
    if tab is None:
        return []
    l = tab.find_all("span", {"class": "ingredient-link-wrapper"})
    links = filter(lambda s: s.a is not None, l)
    return [s.a.contents[0].strip().strip(" *") for s in links]

def get_included(soup) -> List[GiftProduct]:
    tab = soup.find("div", {"id": "tab-description"})
    gifts = tab.find_all("div", {"class": "col-12 col-lg-6"})
    result = []
    for g in gifts:
        product = GiftProduct()
        product.name = g.find("div", {"class": "gift-component-header font-weight-bold"}).string.strip()
        info = g.find("div", {"class": "gift-component-category"}).string.split("(")
        product.type = info[0].strip()
        size_unit = info[1].strip().strip(" )")
        product.size, product.unit = split_unit(size_unit)
        result.append(product)
    return result

def get_page(url: str) -> str:
    h = hashlib.sha256(url.encode("utf-8"))
    filename = h.hexdigest() + ".html"
    page_text = None
    if not os.path.isfile(f"cached_pages/{filename}"):
        page_text = requests.get(url, headers=headers).text
        with open(os.path.join(cache_path, filename), "w") as f:
            f.write(page_text)
    else:
        with open(os.path.join(cache_path, filename)) as file:
            page_text = file.read()
    return page_text

baseurl = "https://www.lushusa.com"
paths = [("bath-shower", "bath-shower"),
         ("hair", "all-hair"),
         ("face", "all-face"),
         ("body", "all-body"),
         ("fragrances/perfume", "perfumes"),
         ("fragrances/body-sprays", "bodysprays"),
         ("gifts/all-gift-sets", "wrapped")]
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.30 Safari/537.36"
}

productlinks = []

for path, cgid in paths:
    url = f"{baseurl}/{path}/?cgid={cgid}&start=0&sz=1000"
    page_text = get_page(url)
    soup = BeautifulSoup(page_text, "html.parser")
    productlist = soup.find_all("h3", {"class": "product-tile-name"})

    for product in productlist:
        href = product.find("a", {"class": "link"}).get("href")
        productlinks.append(baseurl + href)

scraped = set()
products = []
for pl in productlinks:
    if pl in scraped:
        continue
    page_text = get_page(pl)
    soup = BeautifulSoup(page_text, "html.parser")
    is_gift = get_product_type(soup) == "Gift Set"
    product = GiftSet() if is_gift else Product()
    product.name = get_name(soup)
    product.type = get_product_type(soup)
    product.top_description = get_top_description(soup)
    product.prices = get_prices(soup)
    if is_gift:
        product.included = get_included(soup)
    else:
        product.description = get_description(soup)
        product.benefits = get_benefits(soup)
        product.scent = get_scent(soup)
        product.usage = get_usage(soup)
        product.ingredients = get_ingredients(soup)
    products.append(product)
    scraped.add(pl)

with open("data.json", "w") as f:
    for p in products:
        f.write(json.dumps(p, default=lambda o: o.__dict__, indent=2))
