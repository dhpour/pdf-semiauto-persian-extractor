import streamlit as st
import pdfplumber
import fitz
import os
import tempfile
import re
import string

class PDFProcessor:
    def __init__(self):
        self.doctr_model = None
        self.temp_pdf_path = None
        self.doc = None
        self.latin_digits = "123456789098764321"
        self.farsi_digits = "۱۲۳۴۵۶۷۸۹۰٩٨٧٦٤٣٢١"
        self.repl = str.maketrans(self.farsi_digits, self.latin_digits)
    
    def init_doctr(self):
        if self.doctr_model is None:
            from doctr.io import DocumentFile
            from doctr.models import ocr_predictor
            self.doctr_model = ocr_predictor(pretrained=True)
    
    def load_document(self, pdf_path):
        if self.doc:
            self.doc.close()
        self.doc = fitz.open(pdf_path)
        return len(self.doc)

    def reverse_match_plumber(self, match):
        return match.group(0)[::-1]
        
    def justifies_lefties_plumber(self, txt):
        new_txt = txt.translate(self.repl)
        new_txt = re.sub('[A-Za-z' + string.punctuation + ']+', self.reverse_match_plumber, new_txt)
        new_txt = re.sub(r'\d+', self.reverse_match_plumber, new_txt)
        return new_txt

    def adjust_plumber_text(self, text):
        tmp = [x.translate(self.repl) for x in ''.join(list(reversed(list(text)))).split("\n")[::-1]]
        return '\n'.join(tmp)

    def process_with_pdfplumber(self, pdf_path):
        results = []
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                results.append({
                    "page": page_num + 1,
                    "text": self.adjust_plumber_text(text) if text else "No text extracted"
                })
        print('pages: ', len(results))
        return results
    
    def process_with_pymupdf(self, pdf_path):
        results = []
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            text = page.get_text()
            results.append({
                "page": page_num + 1,
                "text": text if text else "No text extracted"
            })
        return results
    
    def process_with_doctr(self, pdf_path):
        try:
            self.init_doctr()
            from doctr.io import DocumentFile
            
            results = []
            document = DocumentFile.from_pdf(pdf_path)
            result = self.doctr_model(document)
            for page_num, page in enumerate(result.pages):
                text = page.export()
                results.append({
                    "page": page_num + 1,
                    "text": text if text else "No text extracted"
                })
            return results
        except ImportError:
            return [{"page": 1, "text": "doctr is not installed. Install with: pip install python-doctr"}]
    
    def cleanup(self):
        if self.doc:
            self.doc.close()
            self.doc = None
        if self.temp_pdf_path and os.path.exists(self.temp_pdf_path):
            try:
                os.remove(self.temp_pdf_path)
            except PermissionError:
                pass

@st.cache_resource
def get_processor():
    return PDFProcessor()

def process_pdf(processor, pdf_path, extraction_method):
    results = []
    
    if extraction_method == "pdfplumber" or extraction_method == "All Methods":
        plumber_results = processor.process_with_pdfplumber(pdf_path)
        for r in plumber_results:
            r["method"] = "pdfplumber"
        results.extend(plumber_results)
    
    if extraction_method == "PyMuPDF" or extraction_method == "All Methods":
        pymupdf_results = processor.process_with_pymupdf(pdf_path)
        for r in pymupdf_results:
            r["method"] = "PyMuPDF"
        results.extend(pymupdf_results)
    
    if extraction_method in ["doctr (OCR)", "All Methods"]:
        doctr_results = processor.process_with_doctr(pdf_path)
        for r in doctr_results:
            r["method"] = "doctr"
        results.extend(doctr_results)
    
    return results

def main():
    st.set_page_config(layout="wide")
    st.title("PDF Content Extractor")
    
    processor = get_processor()
    
    # Initialize session states
    if 'page_num' not in st.session_state:
        st.session_state.page_num = 1
    if 'results' not in st.session_state:
        st.session_state.results = None
    if 'total_pages' not in st.session_state:
        st.session_state.total_pages = 0
    
    # Sidebar configuration
    st.sidebar.header("Configuration")
    extraction_methods = ["pdfplumber", "PyMuPDF"]
    try:
        import doctr
        extraction_methods.extend(["doctr (OCR)", "All Methods"])
    except ImportError:
        pass
    
    extraction_method = st.sidebar.radio("Select Extraction Method", extraction_methods)
    
    uploaded_file = st.sidebar.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file is not None:
        # Process PDF only if it's a new file or extraction method changed
        file_contents = uploaded_file.getvalue()
        current_file_hash = hash(file_contents)
        
        if ('file_hash' not in st.session_state or 
            st.session_state.file_hash != current_file_hash or
            'extraction_method' not in st.session_state or
            st.session_state.extraction_method != extraction_method):
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(file_contents)
                processor.temp_pdf_path = tmp_file.name
            
            # Load document and process PDF
            st.session_state.total_pages = processor.load_document(processor.temp_pdf_path)
            st.session_state.results = process_pdf(processor, processor.temp_pdf_path, extraction_method)
            st.session_state.file_hash = current_file_hash
            st.session_state.extraction_method = extraction_method
        
        # Navigation controls
        st.sidebar.header("Navigation")
        
        # Navigation functions
        def next_page():
            st.session_state.page_num = min(st.session_state.total_pages, st.session_state.page_num + 1)
        
        def prev_page():
            st.session_state.page_num = max(1, st.session_state.page_num - 1)
        
        def first_page():
            st.session_state.page_num = 1
        
        def last_page():
            st.session_state.page_num = st.session_state.total_pages
        
        # Option 1: Slider
        st.session_state.page_num = st.sidebar.slider(
            "Page",
            min_value=1,
            max_value=st.session_state.total_pages,
            value=st.session_state.page_num
        )

        # Option 2: If you prefer to keep the number input instead of the slider
        # Uncomment this and comment out the slider above
        """
        st.sidebar.number_input(
            "Page", 
            min_value=1, 
            max_value=st.session_state.total_pages,
            value=st.session_state.page_num,
            key="page_input",
            on_change=lambda: setattr(st.session_state, 'page_num', st.session_state.page_input)
        )
        """

        # Navigation UI
        col1, col2, col3, col4 = st.sidebar.columns(4)
        
        col1.button("⏮️", on_click=first_page)
        col2.button("◀", on_click=prev_page)
        col3.button("▶", on_click=next_page)
        col4.button("⏭️", on_click=last_page)
        
                
        # Display content
        left_col, right_col = st.columns([1, 1])
        
        with right_col:
            st.header(f"PDF Page {st.session_state.page_num}")
            page = processor.doc.load_page(st.session_state.page_num - 1)
            pix = page.get_pixmap()
            img_bytes = pix.tobytes("png")
            st.image(img_bytes, use_column_width=True)
        
        with left_col:
            st.header("Extracted Text")
            page_results = [r for r in st.session_state.results if r["page"] == st.session_state.page_num]
            
            if page_results:
                for result in page_results:
                    method = result["method"]
                    st.subheader(f"{method}")
                    edited_text = st.text_area(
                        f"Edit text if needed",
                        result["text"],
                        key=f"text_{st.session_state.page_num}_{method}"
                    )
            else:
                st.warning(f"No text extracted for page {st.session_state.page_num}")

if __name__ == "__main__":
    main()

# Keep the existing CSS styling
st.markdown("""
<style>
    .stTextArea textarea {
        font-family: monospace !important;
        background-color: rgba(255, 255, 255, 0.9) !important;
        unicode-bidi: bidi-override !important;
        direction: RTL !important;
        /*height: auto !important;*/
        min-height: 700px !important;
        max-height: none !important;
        box-sizing: border-box !important;
    }

    .stImage img {
        max-width: 90%;
        height: auto;
    }
    
    .stHeader {
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

