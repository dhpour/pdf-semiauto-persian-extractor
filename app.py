import streamlit as st
import os
import tempfile
import re
import string
import json
from datetime import datetime
from PDFProcessor import PDFProcessor
from dotenv import load_dotenv
import fitz
import base64
from streamlit_tags import st_tags, st_tags_sidebar
load_dotenv()

def save_session_state():
    # Collect relevant session state data
    save_data = {
        #"page_num": st.session_state.page_num,
        "results": st.session_state.results,
        "total_pages": st.session_state.total_pages,
        "edited_texts": st.session_state.edited_texts,
        "first_human_page": st.session_state.first_human_page,
        #"zoom_level": st.session_state.zoom_level,
        "keywords": st.session_state.keywords,
        "ttypes": st.session_state.ttypes,
        "pairs": st.session_state.pairs,
        "uploaded_filename": st.session_state.get('uploaded_filename', 'Unknown'),
        "extraction_method": st.session_state.get('extraction_method', 'Unknown'),
        "save_timestamp": datetime.now().isoformat()
    }
    
    # Convert to JSON and encode
    json_data = json.dumps(save_data, ensure_ascii=False)
    encoded_data = base64.b64encode(json_data.encode()).decode()
    
    # Create download button
    st.sidebar.download_button(
        label="📥 Save Session State",
        data=json_data, #encoded_data,
        file_name=f"pdf_extractor_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
    )

def load_session_state():
    uploaded_file = st.sidebar.file_uploader("Choose a saved session file", type="json", key=st.session_state["uploader_json_key"])
    if uploaded_file is not None:
        try:
            # Read the file content
            file_content = uploaded_file.read().decode('utf-8')
            
            # Parse JSON
            save_data = json.loads(file_content)
            
            if st.session_state.total_pages != 0 and st.session_state.total_pages != save_data['total_pages']:
                st.error(f'JSON and PDF page number not match: {str(save_data['total_pages'])}:{str(st.session_state.total_pages)}')
            #    uploaded_file = None
            #    return
            else:
                # Restore session state
                for key, value in save_data.items():
                    if key != 'save_timestamp':
                        setattr(st.session_state, key, value)
                
                st.sidebar.success(f"Session state loaded successfully! (Saved on: {save_data['save_timestamp']})")
                
                # Force a rerun to update the UI
                st.rerun()
        except json.JSONDecodeError as e:
            st.sidebar.error(f"Error decoding JSON: {str(e)}")
        except Exception as e:
            st.sidebar.error(f"Error loading session state: {str(e)}")

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
    
    if extraction_method == "pdf2image/tesseract" or extraction_method == "All Methods":
        tesser_results = processor.process_with_pdf2image_tesseract(pdf_path)
        for r in tesser_results:
            r["method"] = "pdf2image/tesseract"
        results.extend(tesser_results)
    
    if extraction_method == "tesseract" or extraction_method == "All Methods":
        tesser_results = processor.process_with_tesseract(pdf_path)
        for r in tesser_results:
            r["method"] = "tesseract"
        results.extend(tesser_results)
    return results
def reset_session():
    st.session_state.page_num = 1
    st.session_state.results = None
    st.session_state.total_pages = 0
    st.session_state.edited_texts = {}
    st.session_state.first_human_page = -1
    st.session_state.zoom_level = 100
    st.session_state.keywords = []
    st.session_state.ttypes = []
    st.session_state.pairs = []
    st.session_state["uploader_pdf_key"] = 1
    st.session_state["uploader_json_key"] = 1000
    
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
    if 'edited_texts' not in st.session_state:
        st.session_state.edited_texts = {}
    if 'first_human_page' not in st.session_state:
        st.session_state.first_human_page = -1
    if 'zoom_level' not in st.session_state:
        st.session_state.zoom_level = 100
    if 'keywords' not in st.session_state:
        st.session_state.keywords = []
    if 'ttypes' not in st.session_state:
        st.session_state.ttypes = []
    if 'pairs' not in st.session_state:
        st.session_state.pairs = []
    if "uploader_pdf_key" not in st.session_state:
        st.session_state["uploader_pdf_key"] = 1
    if "uploader_json_key" not in st.session_state:
        st.session_state["uploader_json_key"] = 1000

    def reset():
        reset_session()
        #for key in st.session_state.keys():
            #del st.session_state[key]
        #processor = get_processor()
        st.session_state["uploader_pdf_key"] += 1
        st.session_state["uploader_json_key"] += 1
        #st.cache_data.clear()
        

        st.rerun()

    st.sidebar.button("New Project", on_click=reset)
    st.sidebar.header("Configuration")
    extraction_methods = ["pdfplumber", "tesseract", "PyMuPDF"] #, "pdf2image/tesseract"]
    try:
        #import doctr
        #extraction_methods.extend(["doctr (OCR)", "All Methods"])
        pass
    except ImportError:
        pass
    
    extraction_method = st.sidebar.radio("Select Extraction Method", extraction_methods)
    
    uploaded_file = st.sidebar.file_uploader("Choose a PDF file", type="pdf", key=st.session_state["uploader_pdf_key"])

    pdf_page_number = processor.load_document(processor.temp_pdf_path)
    if st.session_state.total_pages != 0 and st.session_state.total_pages != pdf_page_number:
        st.error(f'JSON and PDF page number not match: {str(st.session_state.total_pages)}:{str(pdf_page_number)}')
    #    uploaded_file = None
    #else:
    #    st.session_state.total_pages = pdf_page_number

    def parse():
        st.session_state.results = process_pdf(processor, processor.temp_pdf_path, extraction_method)

    st.sidebar.button("Parse", on_click=parse)

    if uploaded_file is not None:

        # Store filename in session state
        st.session_state.uploaded_filename = uploaded_file.name

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
            #if st.session_state.parse_pdf:            
                #st.session_state.results = process_pdf(processor, processor.temp_pdf_path, extraction_method)
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
        #st.sidebar.number_input(
        #    "Page", 
        #    min_value=1, 
        #    max_value=st.session_state.total_pages,
        #    value=st.session_state.page_num,
        #    key="page_input",
        #    on_change=lambda: setattr(st.session_state, 'page_num', st.session_state.page_input)
        #)
        

        # Navigation UI
        col1, col2, col3, col4 = st.sidebar.columns(4)
        
        col1.button("⏮️", on_click=first_page)
        col2.button("◀", on_click=prev_page)
        col3.button("▶", on_click=next_page)
        col4.button("⏭️", on_click=last_page)
        
        # Add download button to sidebar
        st.sidebar.markdown("---")
        st.sidebar.header("Export")
        #download_json_button()

        #st.sidebar.markdown("---")
        #st.sidebar.subheader("Session Management")
        
        # Save button
        save_session_state()

        
        # Display content
        left_col, right_col = st.columns([1, 1])
        
        with right_col:
            #st.header(f"PDF Page {st.session_state.page_num}")
            st.subheader(f"PDF page {st.session_state.page_num}")

            #zoom_level = st.slider("Zoom (%)", min_value=50, max_value=200, value=st.session_state.zoom_level, step=10, key="zoom_slider")
            zoom_level = st.number_input(
                "Page", 
                min_value=50, 
                max_value=200,
                value=st.session_state.zoom_level,
                step=10,
                key="zoom_input",
                #on_change=lambda: setattr(st.session_state, 'page_num', st.session_state.page_input)
            )
            #st.session_state.zoom_level = zoom_level

            page = processor.doc.load_page(st.session_state.page_num - 1)
            pix = page.get_pixmap()
            #pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_bytes = pix.tobytes("png")

            # Convert image bytes to base64 for embedding in HTML
            img_base64 = base64.b64encode(img_bytes).decode()

            # Embed image in custom HTML with JavaScript for zoom control
            #custom_html = f""""""
            with open("custom_html.html",'r') as f: 
                custom_html = f.read()
            custom_html = custom_html.format(zoom_level=zoom_level, img_base64=img_base64)
            st.components.v1.html(custom_html, height=600, scrolling=False)

            #st.image(img_bytes, use_column_width=True)
        
        def update_text(method):
            text_key = f"text_{st.session_state.page_num}_{method}"
            # Update the edited_texts dictionary with the new text
            page_method_key = f"{st.session_state.page_num}_{method}"
            st.session_state.edited_texts[page_method_key] = st.session_state[text_key]
            
            # Also update the results list for consistency
            for result in st.session_state.results:
                if result["page"] == st.session_state.page_num and result["method"] == method:
                    result["text"] = st.session_state[text_key]
                    break

        def set_human_page():
            st.session_state.first_human_page = st.session_state.page_num
            print(st.session_state.first_human_page)

        with left_col:
            #st.header("Extracted Text")
            if st.session_state.results:
                page_results = [r for r in st.session_state.results if r["page"] == st.session_state.page_num]
                
                st.sidebar.button(
                    label="Set current page as 1st human page",
                    on_click=set_human_page
                )
                st.sidebar.text('Current human page number: ' + str(st.session_state.page_num - st.session_state.first_human_page + 1 if (st.session_state.first_human_page > 0 and st.session_state.page_num - st.session_state.first_human_page >= 0) else -1))
                st.sidebar.text('First human page (offset): ' + str(st.session_state.first_human_page))
                #st.sidebar.text()

                if page_results:
                    for result in page_results:
                        method = result["method"]
                        #st.subheader(f"{method}")
                        st.subheader("Page text:")

                        # Create a unique key for the text area
                        text_key = f"text_{st.session_state.page_num}_{method}"
                        page_method_key = f"{st.session_state.page_num}_{method}"
                        
                        # Get the text from edited_texts if it exists, otherwise from result
                        if page_method_key in st.session_state.edited_texts:
                            current_text = st.session_state.edited_texts[page_method_key]
                            # Show indicator that text has been edited
                            st.info("This text has been edited. Changes are saved automatically.")
                        else:
                            current_text = result["text"]
                        
                        # Update session state
                        st.session_state[text_key] = current_text
                        
                        # Display the text area
                        edited_text = st.text_area(
                            f"Edit text if needed",
                            value=current_text,
                            key=text_key,
                            on_change=update_text,
                            args=(method,)
                        )

                        keywords = st_tags_sidebar(
                            label='keywords:',
                            text='Press enter to add more',
                            value=st.session_state.keywords,
                            suggestions=[],
                            maxtags = 10,
                            key='keywords')
                        #st.session_state.keywords = keywords
                        pairs = st_tags_sidebar(
                            label='pairs:',
                            text='Press enter to add more',
                            value=st.session_state.pairs,
                            suggestions=[],
                            maxtags = 10,
                            key='pairs')
                        #st.session_state.pairs = pairs
                        ttypes = st_tags_sidebar(
                            label='type:',
                            text='Press enter to add more',
                            value=st.session_state.ttypes,
                            suggestions=[],
                            maxtags = 10,
                            key='ttypes')
                        #st.session_state.ttypes = ttypes
                        
                else:
                    st.warning(f"No text extracted for page {st.session_state.page_num}")

     # Load functionality
    st.sidebar.markdown("---")
    st.sidebar.subheader("Import JSON")
    load_session_state()
    # Add debug information
    if os.getenv('DEBUG', 'False').lower() in ('true'):
        with st.expander("Debug Information", expanded=False):
            st.write("Session state edited_texts:", st.session_state.edited_texts)
            st.write("Current page:", st.session_state.page_num)
            st.write("Human 1st Page:", st.session_state.first_human_page)
            st.write("Human Page Number:", st.session_state.page_num - st.session_state.first_human_page + 1 if (st.session_state.first_human_page > 0 and st.session_state.page_num - st.session_state.first_human_page >= 0) else -1)
            st.write("keywords:", st.session_state.keywords)
            st.write("pairs:", st.session_state.pairs)
            st.write("ttypes:", st.session_state.ttypes)
            if st.session_state.results:
                st.write("Number of pages:", len(st.session_state.results))
                st.write("Available methods:", list(set(r["method"] for r in st.session_state.results)))
            st.write("SESSION: ", st.session_state)

if __name__ == "__main__":
    main()

# Keep the existing CSS styling
with open("css.html",'r') as f: 
    custom_css = f.read()
    st.markdown(custom_css, unsafe_allow_html=True)
