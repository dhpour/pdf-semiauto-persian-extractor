# PDF extraction text review

features
--------
- Change each page text
- Download the whole pdf pages text (including changes) in JSON format
- Set human page number for all pages with setting the offset
- Multi library for text and OCR.
- Compatible with Persian (and Arabic) right to left scripts.

usage
---
`streamlit run app.py`

config
------
set `TESSER_ENGINE` and `PDF2IMAGE_ENGINE` in `.env` for using these libraries if they are not set in environemnt variables already.
