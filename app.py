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
import streamlit.components.v1 as components
import base64

load_dotenv()


def get_all_text_data():
    all_data = {
        "metadata": {
            "export_date": datetime.now().isoformat(),
            "filename": st.session_state.get('uploaded_filename', 'Unknown'),
            "total_pages": st.session_state.total_pages,
            "extraction_method": st.session_state.extraction_method
        },
        "pages": []
    }
    
    # Combine original results with edited texts
    for page_num in range(1, st.session_state.total_pages + 1):
        page_data = {
            "page_number": page_num,
            "extractions": []
        }
        if st.session_state.first_human_page != -1:
            page_data['human_page_number'] = page_num - st.session_state.first_human_page + 1 if page_num - st.session_state.first_human_page >= 0 else -1
        
        # Get results for this page
        page_results = [r for r in st.session_state.results if r["page"] == page_num]
        
        for result in page_results:
            method = result["method"]
            page_method_key = f"{page_num}_{method}"
            
            # Use edited text if available, otherwise use original
            text = st.session_state.edited_texts.get(page_method_key, result["text"])
            
            extraction_data = {
                "method": method,
                "text": text,
                "is_edited": page_method_key in st.session_state.edited_texts
            }
            page_data["extractions"].append(extraction_data)
        
        all_data["pages"].append(page_data)
    
    return all_data

def download_json_button():
    if st.session_state.results:
        all_data = get_all_text_data()
        json_str = json.dumps(all_data, ensure_ascii=False, indent=2)
        
        st.sidebar.download_button(
            label="📥 Download Extracted Text (JSON)",
            data=json_str,
            file_name=all_data['metadata']['filename'].split('.pdf')[0]+'.json',
            mime="application/json",
        )

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

    # Sidebar configuration
    st.sidebar.header("Configuration")
    extraction_methods = ["pdfplumber", "tesseract", "PyMuPDF"] #, "pdf2image/tesseract"]
    try:
        #import doctr
        #extraction_methods.extend(["doctr (OCR)", "All Methods"])
        pass
    except ImportError:
        pass
    
    extraction_method = st.sidebar.radio("Select Extraction Method", extraction_methods)
    
    uploaded_file = st.sidebar.file_uploader("Choose a PDF file", type="pdf")
    
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
        download_json_button()

        # Display content
        left_col, right_col = st.columns([1, 1])
        
        with right_col:
            #st.header(f"PDF Page {st.session_state.page_num}")
            st.subheader(f"PDF page {st.session_state.page_num}")

            zoom_level = st.slider("Zoom (%)", min_value=50, max_value=200, value=st.session_state.zoom_level, step=10, key="zoom_slider")
            zoom_level = st.number_input(
                "Page", 
                min_value=50, 
                max_value=200,
                value=st.session_state.zoom_level,
                step=10,
                key="zoom_input",
                #on_change=lambda: setattr(st.session_state, 'page_num', st.session_state.page_input)
            )
            st.session_state.zoom_level = zoom_level

            page = processor.doc.load_page(st.session_state.page_num - 1)
            pix = page.get_pixmap()
            #pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_bytes = pix.tobytes("png")

            # Convert image bytes to base64 for embedding in HTML
            img_base64 = base64.b64encode(img_bytes).decode()

            # Embed image in custom HTML with JavaScript for zoom control
            custom_html = f"""
            <div id="pdf-container" style="width: 100%; height: 600px; overflow: hidden; position: relative;">
                <img id="pdf-image" src="data:image/png;base64,{img_base64}" style="position: absolute; left: 0; top: 0;">
            </div>

            <script>
            const container = document.getElementById('pdf-container');
            const img = document.getElementById('pdf-image');
            let isDragging = false;
            let startX, startY, translateX = 0, translateY = 0;

            function setImageSize() {{
                const zoom = {zoom_level} / 100;
                img.style.width = `${{img.naturalWidth * zoom}}px`;
                img.style.height = `${{img.naturalHeight * zoom}}px`;
            }}

            function clamp(value, min, max) {{
                return Math.min(Math.max(value, min), max);
            }}

            function updateImagePosition() {{
                const containerRect = container.getBoundingClientRect();
                const imgRect = img.getBoundingClientRect();

                translateX = clamp(translateX, containerRect.width - imgRect.width, 0);
                translateY = clamp(translateY, containerRect.height - imgRect.height, 0);

                img.style.transform = `translate(${{translateX}}px, ${{translateY}}px)`;
            }}

            container.addEventListener('mousedown', (e) => {{
                isDragging = true;
                startX = e.clientX - translateX;
                startY = e.clientY - translateY;
                container.style.cursor = 'grabbing';
            }});

            container.addEventListener('mousemove', (e) => {{
                if (!isDragging) return;
                translateX = e.clientX - startX;
                translateY = e.clientY - startY;
                updateImagePosition();
            }});

            container.addEventListener('mouseup', () => {{
                isDragging = false;
                container.style.cursor = 'grab';
            }});

            container.addEventListener('mouseleave', () => {{
                isDragging = false;
                container.style.cursor = 'grab';
            }});

            // Prevent default drag behavior
            img.addEventListener('dragstart', (e) => e.preventDefault());

            // Initial setup
            setImageSize();
            updateImagePosition();
            container.style.cursor = 'grab';
            </script>
            """
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
            else:
                st.warning(f"No text extracted for page {st.session_state.page_num}")

    # Add debug information
    if os.getenv('DEBUG', 'False').lower() in ('true'):
        with st.expander("Debug Information", expanded=False):
            st.write("Session state edited_texts:", st.session_state.edited_texts)
            st.write("Current page:", st.session_state.page_num)
            st.write("Human 1st Page:", st.session_state.first_human_page)
            st.write("Human Page Number:", st.session_state.page_num - st.session_state.first_human_page + 1 if (st.session_state.first_human_page > 0 and st.session_state.page_num - st.session_state.first_human_page >= 0) else -1)
            if st.session_state.results:
                st.write("Number of pages:", len(st.session_state.results))
                st.write("Available methods:", list(set(r["method"] for r in st.session_state.results)))

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
        min-height: 900px !important;
        max-height: none !important;
        box-sizing: border-box !important;
        font-size: 22px;
    }

    .stSlider {
        padding-bottom: 2rem;
    }
    .stImage {
        margin-top: 1rem;
    }
    .element-container {
        overflow-x: auto;
    }
    
    /*.stHeader {
        margin-bottom: 1rem;
    }*/

    /* Style for the download button in sidebar */
    .sidebar .stDownloadButton button {
        width: 100%;
        /*margin-top: 0.5rem;*/
    }

    #pdf-container {
        border: 1px solid #ddd;
        box-shadow: 0 0 10px rgba(0,0,0,0.1);
    }

    #pdf-image {
        user-select: none;
        -webkit-user-drag: none;
    }
</style>
""", unsafe_allow_html=True)
