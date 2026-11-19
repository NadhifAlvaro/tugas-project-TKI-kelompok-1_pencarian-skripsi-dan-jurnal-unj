"""
Panen metadata repositori UNJ (EPrints) lewat OAI-PMH, simpan ke CSV.

Cara pakai:
    pip install requests
    python harvest_unj.py --test            # cek endpoint aktif atau tidak
    python harvest_unj.py --max 2000        # panen maksimal 2000 record

Catatan:
- Cek dulu robots.txt dan ketentuan situs. Beri jeda antar request.
- Nama penulis/pembimbing sengaja TIDAK disimpan (anonimisasi).
- Jika BASE_URL tidak aktif, cek alamat OAI di halaman repositori
  atau pakai scraping sebagai cadangan.
"""
import argparse
import csv
import re
import time
import xml.etree.ElementTree as ET

import requests

BASE_URL = "https://repository.unj.ac.id/cgi/oai2"  # umumnya untuk EPrints; verifikasi dulu
DELAY = 1.5  # detik antar request
HEADERS = {"User-Agent": "Tugas-Kuliah-TKI-UNJ (akademik, non-komersial)"}

NS = {
    "oai": "http://www.openarchives.org/OAI/2.0/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/",
}


def get(params):
    r = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=60)
    r.raise_for_status()
    return ET.fromstring(r.content)


def texts(parent, tag):
    return [e.text.strip() for e in parent.findall(f"dc:{tag}", NS) if e.text]


def clean(t):
    """Rapikan spasi dan baris baru jadi satu baris."""
    return re.sub(r"\s+", " ", t or "").strip()


def decode_set(s):
    """setSpec EPrints berupa heksadesimal, mis. 74797065733D... -> types=thesis."""
    try:
        return bytes.fromhex(s).decode("utf-8")
    except Exception:
        return s


def parse_record(rec):
    header = rec.find("oai:header", NS)
    if header is not None and header.get("status") == "deleted":
        return None
    dc = rec.find(".//oai_dc:dc", NS)
    if dc is None:
        return None
    sets = [decode_set(s.text) for s in header.findall("oai:setSpec", NS) if s.text]
    ids = texts(dc, "identifier")
    url = next((i for i in ids if i.startswith("http")), "")

    # Abstrak = description terpanjang. Di EPrints UNJ, kutipan sitasi
    # (memuat nama penulis) sering menempel di awal abstrak, berakhir di
    # "Universitas Negeri Jakarta, <tahun>." -> potong dan buang.
    descs = [clean(d) for d in texts(dc, "description")]
    abstrak = max(descs, key=len) if descs else ""
    prodi = ""
    m = re.search(r"Universitas Negeri Jakarta,?\s*(?:19|20)\d{2}\.", abstrak[:600])
    if m:
        sitasi = abstrak[:m.end()]
        abstrak = abstrak[m.end():].strip()
        mp = re.search(r"Program Studi (.+?)(?:\s+Jurusan|,|\.|\s+Universitas)", sitasi)
        prodi = mp.group(1).strip() if mp else ""

    return {
        "oai_id": header.findtext("oai:identifier", default="", namespaces=NS),
        "judul": clean(" ".join(texts(dc, "title"))),
        "abstrak": abstrak,
        "kata_kunci": clean("; ".join(texts(dc, "subject"))),
        "tahun": (texts(dc, "date") or [""])[0][:4],
        "prodi": prodi,
        "jenis": clean("; ".join(texts(dc, "type"))),
        "set": clean("; ".join(sets)),
        "url": url,
        # creator/contributor tidak disimpan (anonimisasi)
    }


def harvest(max_records, out_path):
    fields = ["oai_id", "judul", "abstrak", "kata_kunci", "tahun", "prodi", "jenis", "set", "url"]
    n = 0
    token = None
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        while n < max_records:
            params = ({"verb": "ListRecords", "resumptionToken": token}
                      if token else {"verb": "ListRecords", "metadataPrefix": "oai_dc"})
            root = get(params)
            err = root.find("oai:error", NS)
            if err is not None:
                print("Error OAI:", err.get("code"), err.text)
                break
            lr = root.find("oai:ListRecords", NS)
            for rec in lr.findall("oai:record", NS):
                row = parse_record(rec)
                if row and row["judul"] and row["abstrak"]:  # hanya yang punya abstrak
                    w.writerow(row)
                    n += 1
                    if n >= max_records:
                        break
            rt = lr.find("oai:resumptionToken", NS)
            token = rt.text.strip() if rt is not None and rt.text else None
            print(f"Terkumpul: {n}")
            if not token:
                break
            time.sleep(DELAY)
    print(f"Selesai. {n} record disimpan di {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="cek endpoint (Identify)")
    ap.add_argument("--max", type=int, default=2000)
    ap.add_argument("--out", default="dataset_unj.csv")
    args = ap.parse_args()

    if args.test:
        root = get({"verb": "Identify"})
        print(ET.tostring(root, encoding="unicode")[:1500])
        return
    harvest(args.max, args.out)


if __name__ == "__main__":
    main()
