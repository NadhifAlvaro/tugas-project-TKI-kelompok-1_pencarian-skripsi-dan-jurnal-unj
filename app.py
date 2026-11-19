"""Antarmuka web sederhana (Streamlit). Jalankan: streamlit run app.py"""
import streamlit as st

from search_engine import DEFAULT_WEIGHTS, SearchEngine

st.set_page_config(page_title="Pencarian Skripsi UNJ", page_icon="🔎", layout="wide")


@st.cache_resource(show_spinner="Memuat data dan membangun index (hanya sekali)...")
def load_engine():
    return SearchEngine("data/dataset_clean.csv", "data/tokens_cache.pkl")


engine = load_engine()
years = sorted(engine.df["tahun"].unique())
years = [y for y in years if y > 0]

st.title("🔎 Pencarian Skripsi UNJ")
st.caption(f"{len(engine.df)} dokumen dari repositori UNJ. Inverted index dan ranking dibangun sendiri (TF-IDF dan BM25).")

# ---------------- sidebar: pengaturan ----------------
with st.sidebar:
    st.header("Pengaturan")
    model = st.radio("Model ranking", ["bm25", "tfidf"], format_func=lambda m: "BM25" if m == "bm25" else "TF-IDF (kosinus)")
    k = st.slider("Jumlah hasil", 5, 30, 10)
    st.subheader("Bobot field")
    w_judul = st.slider("Judul", 0.0, 5.0, DEFAULT_WEIGHTS["judul"], 0.5)
    w_kk = st.slider("Kata kunci", 0.0, 5.0, DEFAULT_WEIGHTS["kata_kunci"], 0.5)
    w_abs = st.slider("Abstrak", 0.0, 5.0, DEFAULT_WEIGHTS["abstrak"], 0.5)
    st.subheader("Filter tahun")
    y_min, y_max = st.select_slider("Rentang tahun", options=years, value=(years[0], years[-1]))

weights = {"judul": w_judul, "kata_kunci": w_kk, "abstrak": w_abs}

# ---------------- pencarian ----------------
query = st.text_input("Ketik topik skripsi", placeholder="contoh: motivasi belajar siswa")

if "similar_to" not in st.session_state:
    st.session_state["similar_to"] = None


def show_doc(r, prefix, show_fields=True):
    st.markdown(f"**{r['judul']}**  \n*Tahun {r['tahun']}* | skor: `{r['skor']:.4f}`")
    if show_fields and r.get("skor_field"):
        sf = r["skor_field"]
        st.caption(f"Skor per field (0-1): judul {sf['judul']:.2f} | kata kunci {sf['kata_kunci']:.2f} | abstrak {sf['abstrak']:.2f}")
    with st.expander("Lihat abstrak"):
        st.write(r["abstrak"])
        st.markdown(f"[Buka di repositori]({r['url']})")
    if st.button("Dokumen serupa", key=f"{prefix}_{r['doc_id']}"):
        st.session_state["similar_to"] = r["doc_id"]
        st.rerun()


if query.strip():
    t_results = engine.search(query, model=model, k=k, weights=weights, year_min=y_min, year_max=y_max)
    st.subheader(f"Hasil untuk: \"{query}\" ({len(t_results)} dokumen)")
    st.caption("Kata kunci setelah pre-processing: " + ", ".join(engine.preprocess(query)))
    if not t_results:
        st.warning("Tidak ada dokumen yang cocok. Coba kata kunci lain atau periksa ejaan.")
    for i, r in enumerate(t_results, 1):
        st.markdown(f"##### {i}.")
        show_doc(r, "hasil")
        st.divider()

sim_id = st.session_state["similar_to"]
if sim_id is not None:
    base = engine.df_idx.loc[sim_id, "judul"]
    st.subheader(f"Dokumen serupa dengan: {base}")
    for i, r in enumerate(engine.similar(sim_id, k=5), 1):
        st.markdown(f"##### {i}.")
        show_doc(r, "serupa", show_fields=False)
    if st.button("Tutup dokumen serupa"):
        st.session_state["similar_to"] = None
        st.rerun()
