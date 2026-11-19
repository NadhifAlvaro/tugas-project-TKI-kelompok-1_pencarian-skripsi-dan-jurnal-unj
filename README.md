# Mesin Pencari Skripsi UNJ

Tugas Project Mata Kuliah Temu Kembali Informasi, Program Studi Sistem dan Teknologi Informasi, Universitas Negeri Jakarta.
Topik 1: Pencarian Skripsi dan Jurnal UNJ. Kelompok: [nomor/nama kelompok].

Sistem mencari judul dan abstrak skripsi dari repositori UNJ. Inverted index dan model ranking (TF-IDF dan BM25) dibangun sendiri. Library luar hanya dipakai untuk stemming Bahasa Indonesia (Sastrawi) dan antarmuka web (Streamlit).

## Fitur
- Pre-processing: case folding, tokenisasi, stopword (Indonesia dan Inggris), stemming Sastrawi
- Inverted index per field (judul, kata kunci, abstrak)
- Dua model ranking: TF-IDF (kosinus) dan BM25, dengan bobot per field yang bisa diubah
- Fitur dokumen serupa (kemiripan kosinus)
- Filter tahun
- Antarmuka web yang menampilkan hasil beserta skor

## Cara menjalankan

Syarat: Python 3.9 atau lebih baru.

```bash
# 1. Unduh repositori ini
git clone https://github.com/<username>/<nama-repo>.git
cd <nama-repo>

# 2. (Disarankan) buat virtual environment
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate

# 3. Pasang library
pip install -r requirements.txt

# 4. Jalankan aplikasi
streamlit run app.py
```

Browser akan terbuka otomatis di `http://localhost:8501`. Jalankan pertama kali butuh beberapa detik untuk membangun index.

## Struktur repositori

| File / folder | Isi |
|---|---|
| `app.py` | Antarmuka web (Streamlit) |
| `search_engine.py` | Pre-processing, inverted index, TF-IDF, BM25, dokumen serupa |
| `data/dataset_clean.csv` | Dataset bersih (1.988 skripsi UNJ) |
| `data/queries_uji.csv` | 20 query uji |
| `harvest_unj.py` | Skrip pengambilan data dari repositori UNJ lewat OAI-PMH |
| `notebook_cleaning_sampai_checkpoint2.ipynb` | Notebook cleaning, index, dan ranking |

## Data
- Sumber: repositori UNJ (repository.unj.ac.id), diambil lewat OAI-PMH. Tanggal pengambilan: [isi tanggal].
- Nama penulis dan pembimbing tidak disimpan (anonimisasi).
- Keterbatasan: dokumen terkonsentrasi pada tahun 2012-2018, dan seluruhnya non-peer-reviewed.

## Penggunaan alat AI dan sumber luar
- [Tuliskan alat AI yang dipakai dan untuk apa, mis. bantuan Claude untuk kerangka kode dan penjelasan.]
- Sastrawi (stemmer dan stopword Bahasa Indonesia), Streamlit, pandas.

## Kontribusi anggota
| Nama | Peran |
|---|---|
| [n] | Data |
| nadhif dobry alvaro | Core IR |
| raditya dandi maulana | Antarmuka dan fitur |
| [nama] | Evaluasi dan laporan |
