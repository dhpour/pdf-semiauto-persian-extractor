# PDF text extractor for Arabic scripts

features
--------
- Changing each page text
- Downloading the whole pdf pages text (including changes) in JSON format
- Setting human page number for all pages by setting the offset
- Compatible with Persian (and Arabic) right to left scripts.
- Converting arabic script contextual character forms into the general form (e.g. converts `ﺑ`, `ﺒ`, `ﺐ` into `ب` or `ﻫ`, `ﻬ`, `ﻪ` into `ه`)
- Supporting mutiple libraries for text extraction (both text-based and OCR-based)
    - pdfplumber
    - tesseract
    - PyMuPDF
    - surya
- Adding keywords and tags to the whole extracted JSON and to the pages.
- Removing diacritics.
- Replacing custom strings.
- Reopening and editing JSON export.
- Building index object for specific pdfs.

usage
---
`streamlit run app.py`

config
------
set `TESSER_ENGINE` and `PDF2IMAGE_ENGINE` in `.env` for using these libraries.
