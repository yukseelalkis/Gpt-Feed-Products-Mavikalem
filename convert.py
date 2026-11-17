#!/usr/bin/env python3
"""IdeaSoft Google Merchant XML feed -> ChatGPT Business Hub TSV."""
import csv, html, re, sys, urllib.request
import xml.etree.ElementTree as ET

FIELDS = ["item_id", "title", "description", "url", "brand", "seller_name", "image_url",
          "additional_image_urls", "availability", "price", "gtin", "mpn",
          "target_countries", "store_country"]
AVAIL = {"in stock": "in_stock", "instock": "in_stock", "out of stock": "out_of_stock",
         "outofstock": "out_of_stock", "preorder": "pre_order", "pre order": "pre_order",
         "back order": "backorder"}
SELLER, COUNTRY = "MaviKalem", "TR"

def local(tag):
    return tag.rsplit("}", 1)[-1].lower()

def clean(text, limit=None):
    t = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    t = re.sub(r"\s+", " ", t).strip()
    return t[:limit] if limit else t

def norm_price(p):
    return re.sub(r"\s+", " ", (p or "").replace(",", ".")).strip()

def amount(p):
    m = re.match(r"\d+(\.\d+)?", p or "")
    return float(m.group()) if m else 0.0

def convert(src, out, default_brand):
    w = csv.writer(out, delimiter="\t", lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    w.writerow(FIELDS)
    n = 0
    for _, el in ET.iterparse(src, events=("end",)):
        if local(el.tag) not in ("item", "entry"):
            continue
        d, extra = {}, []
        for c in el:
            k, v = local(c.tag), (c.text or "").strip()
            if k == "additional_image_link":
                extra.append(v)
            elif k not in d:
                d[k] = v
        g = lambda k: d.get(k, "")
        sale = norm_price(g("sale_price"))
        price = sale if amount(sale) > 0 else norm_price(g("price"))  # indirim varsa sitedeki fiyat
        a = g("availability").lower().strip()
        row = {
            "item_id": g("id"),
            "title": clean(g("title"), 150),
            "description": clean(g("description"), 5000) or clean(g("title")),
            "url": g("link"),
            "brand": clean(g("brand")) or default_brand,
            "seller_name": SELLER,
            "image_url": g("image_link"),
            "additional_image_urls": ",".join(x.replace(",", "%2C") for x in extra if x),
            "availability": AVAIL.get(a, a.replace(" ", "_")) or "in_stock",
            "price": price,
            "gtin": g("gtin"), "mpn": g("mpn"),
            "target_countries": COUNTRY, "store_country": COUNTRY,
        }
        for f in FIELDS:
            row[f] = row[f].replace("\t", " ").replace("\n", " ")
        if row["item_id"] and row["url"] and amount(row["price"]) > 0 and row["image_url"]:
            w.writerow([row[f] for f in FIELDS]); n += 1
        el.clear()
    print(f"{n} ürün yazıldı", file=sys.stderr)

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.mavikalem.com.tr/output/8087119590"
    outfile = sys.argv[2] if len(sys.argv) > 2 else "feed.tsv"
    brand = sys.argv[3] if len(sys.argv) > 3 else "MaviKalem"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 feed-converter"})
    with urllib.request.urlopen(req, timeout=120) as r, open(outfile, "w", encoding="utf-8", newline="") as f:
        convert(r, f, brand)