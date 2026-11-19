"""
Mesin pencari skripsi UNJ: pre-processing, inverted index, TF-IDF, BM25, dokumen serupa.
Inverted index dan ranking ditulis sendiri (Python standar). Library luar hanya untuk stemming (Sastrawi).
"""
import heapq
import math
import os
import pickle
import re
from collections import Counter, defaultdict

import pandas as pd
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

FIELDS = ["judul", "kata_kunci", "abstrak"]
DEFAULT_WEIGHTS = {"judul": 3.0, "kata_kunci": 2.0, "abstrak": 1.0}
K1, B = 1.5, 0.75

EN_STOP = set("""a an the and or of to in on at for from by with without as is are was were be been being this that
these those it its into than then so such not no can could may might will would should has have had do does did
which who whom whose what when where why how about between among over under also their there here more most
other some any each both only own same very""".split())


class FieldIndex:
    """Inverted index untuk satu field: term -> {doc_id: tf}."""

    def __init__(self, tokens_by_doc, n_docs):
        self.N = n_docs
        self.postings = defaultdict(dict)
        self.doc_len = {}
        for doc_id, toks in tokens_by_doc.items():
            self.doc_len[doc_id] = len(toks)
            for term, tf in Counter(toks).items():
                self.postings[term][doc_id] = tf
        self.df = {t: len(p) for t, p in self.postings.items()}
        nonempty = sum(1 for l in self.doc_len.values() if l > 0)
        self.avgdl = sum(self.doc_len.values()) / max(1, nonempty)
        sq = defaultdict(float)
        for term, post in self.postings.items():
            idf = self.idf_tfidf(term)
            for d, tf in post.items():
                w = (1 + math.log10(tf)) * idf
                sq[d] += w * w
        self.norm = {d: math.sqrt(v) for d, v in sq.items()}

    def idf_tfidf(self, term):
        return math.log10(self.N / self.df[term])

    def idf_bm25(self, term):
        df = self.df[term]
        return math.log(1 + (self.N - df + 0.5) / (df + 0.5))


def score_tfidf(ix, q_terms):
    qtf = Counter(t for t in q_terms if t in ix.postings)
    if not qtf:
        return {}
    q_w = {t: (1 + math.log10(c)) * ix.idf_tfidf(t) for t, c in qtf.items()}
    q_norm = math.sqrt(sum(w * w for w in q_w.values()))
    if q_norm == 0:
        return {}
    scores = defaultdict(float)
    for t, wq in q_w.items():
        idf = ix.idf_tfidf(t)
        for d, tf in ix.postings[t].items():
            scores[d] += wq * ((1 + math.log10(tf)) * idf)
    return {d: s / (q_norm * ix.norm[d]) for d, s in scores.items() if ix.norm.get(d, 0) > 0}


def score_bm25(ix, q_terms):
    scores = defaultdict(float)
    for t in set(q_terms):
        if t not in ix.postings:
            continue
        idf = ix.idf_bm25(t)
        for d, tf in ix.postings[t].items():
            denom = tf + K1 * (1 - B + B * ix.doc_len[d] / ix.avgdl)
            scores[d] += idf * tf * (K1 + 1) / denom
    return dict(scores)


SCORERS = {"tfidf": score_tfidf, "bm25": score_bm25}


class SearchEngine:
    def __init__(self, csv_path="data/dataset_clean.csv", cache_path="data/tokens_cache.pkl"):
        self.df = pd.read_csv(csv_path).fillna({"kata_kunci": ""})
        self.df_idx = self.df.set_index("doc_id")
        self.stemmer = StemmerFactory().create_stemmer()
        self.stopwords = set(StopWordRemoverFactory().get_stop_words()) | EN_STOP
        self._stem_cache = {}
        self.tokens = self._load_tokens(cache_path)
        n = len(self.df)
        self.index = {f: FieldIndex(self.tokens[f], n) for f in FIELDS}
        # index gabungan semua field, dipakai untuk fitur "dokumen serupa"
        combined = {d: self.tokens["judul"][d] + self.tokens["kata_kunci"][d] + self.tokens["abstrak"][d]
                    for d in self.df["doc_id"]}
        self.combined_tokens = combined
        self.combined_index = FieldIndex(combined, n)

    # ---------- pre-processing ----------
    def _stem(self, w):
        if w not in self._stem_cache:
            self._stem_cache[w] = self.stemmer.stem(w)
        return self._stem_cache[w]

    def preprocess(self, text):
        text = str(text).lower()
        text = re.sub(r"https?://\S+", " ", text)
        toks = [t for t in re.findall(r"[a-z]+", text) if len(t) > 1 and t not in self.stopwords]
        toks = [self._stem(t) for t in toks]
        return [t for t in toks if len(t) > 1 and t not in self.stopwords]

    def _load_tokens(self, cache_path):
        ids = self.df["doc_id"].tolist()
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "rb") as f:
                    data = pickle.load(f)
                if data["doc_ids"] == ids:
                    return data["tokens"]
            except Exception:
                pass
        tokens = {f: {} for f in FIELDS}
        for row in self.df.itertuples(index=False):
            for f in FIELDS:
                tokens[f][row.doc_id] = self.preprocess(getattr(row, f))
        try:
            with open(cache_path, "wb") as f:
                pickle.dump({"doc_ids": ids, "tokens": tokens}, f)
        except OSError:
            pass
        return tokens

    # ---------- pencarian ----------
    def search(self, query, model="bm25", k=10, weights=None, year_min=None, year_max=None):
        """Kembalikan list dict hasil: doc_id, judul, tahun, skor, skor per field, url, abstrak."""
        weights = weights or DEFAULT_WEIGHTS
        q_terms = self.preprocess(query)
        if not q_terms:
            return []
        per_field = {}
        for f in FIELDS:
            s = SCORERS[model](self.index[f], q_terms)
            mx = max(s.values()) if s else 0
            per_field[f] = {d: v / mx for d, v in s.items()} if mx > 0 else {}
        final = defaultdict(float)
        for f in FIELDS:
            for d, v in per_field[f].items():
                final[d] += weights[f] * v
        if year_min is not None or year_max is not None:
            lo = year_min if year_min is not None else -1
            hi = year_max if year_max is not None else 10**6
            final = {d: s for d, s in final.items() if lo <= self.df_idx.loc[d, "tahun"] <= hi}
        top = heapq.nlargest(k, final.items(), key=lambda x: (x[1], -x[0]))
        return [self._row(d, s, {f: per_field[f].get(d, 0.0) for f in FIELDS}) for d, s in top]

    def similar(self, doc_id, k=5):
        """Dokumen serupa: kemiripan kosinus TF-IDF antara dokumen ini dan dokumen lain."""
        toks = self.combined_tokens.get(doc_id, [])
        scores = score_tfidf(self.combined_index, toks)
        scores.pop(doc_id, None)
        top = heapq.nlargest(k, scores.items(), key=lambda x: (x[1], -x[0]))
        return [self._row(d, s, None) for d, s in top]

    def _row(self, d, score, per_field):
        r = self.df_idx.loc[d]
        row = {"doc_id": int(d), "judul": r["judul"], "tahun": int(r["tahun"]), "skor": float(score),
               "url": r["url"], "abstrak": r["abstrak"], "kata_kunci": r["kata_kunci"]}
        if per_field is not None:
            row["skor_field"] = per_field
        return row
