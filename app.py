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
import pandas as pd

load_dotenv()

def save_session_state():
    # Collect relevant session state data
    save_data = {
        #"page_num": st.session_state.page_num,
        "pages": st.session_state.pages,
        "total_pages": st.session_state.total_pages,
        "first_human_page": st.session_state.first_human_page,
        #"zoom_level": st.session_state.zoom_level,
        "keywords": st.session_state.keywords,
        "ttypes": st.session_state.ttypes,
        "ppairs": st.session_state.ppairs,
        "uploaded_filename": st.session_state.get('uploaded_filename', 'Unknown'),
        #"extraction_method": st.session_state.get('extraction_method', 'Unknown'),
        "save_timestamp": datetime.now().isoformat(),
        #"cached_pages": {
            #k: v for k, v in st.session_state.items() 
            #if k.startswith("cached_page_")
        #}
        "book_index": st.session_state.book_index,
    }
    if "book_index_edited" in st.session_state:
        save_data["book_index_edited"] = st.session_state.book_index_edited
    
    if "keywords_edited" in st.session_state:
        save_data["keywords_edited"] = st.session_state.keywords_edited

    if "types_edited" in st.session_state:
        save_data["types_edited"] = st.session_state.types_edited

    if "pairs_edited" in st.session_state:
        save_data["pairs_edited"] = st.session_state.pairs_edited

    # Convert to JSON and encode
    json_data = json.dumps(save_data, ensure_ascii=False)
    encoded_data = base64.b64encode(json_data.encode()).decode()
    
    # Create download button
    st.sidebar.download_button(
        label="📥 Save Session State",
        data=json_data, #encoded_data,
        file_name=f"{st.session_state.get('uploaded_filename', 'Unknown').split('.pdf')[0]}.json",
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
            r["pdfplumber"] = r["text"]
            del r["text"]
        results.extend(plumber_results)
    
    if extraction_method == "PyMuPDF" or extraction_method == "All Methods":
        pymupdf_results = processor.process_with_pymupdf(pdf_path)
        for r in pymupdf_results:
            r["method"] = "PyMuPDF"
            r["PyMuPDF"] = r["text"]
            del r["text"]
        results.extend(pymupdf_results)
    
    if extraction_method in ["doctr (OCR)", "All Methods"]:
        doctr_results = processor.process_with_doctr(pdf_path)
        for r in doctr_results:
            r["method"] = "doctr"
            r["doctr"] = r["text"]
            del r["text"]
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
            r["tesseract"] = r["text"]
            del r["text"]
        results.extend(tesser_results)
    return results
def reset_session():
    st.session_state.page_num = 1
    st.session_state.pages = []
    st.session_state.total_pages = 0
    st.session_state.first_human_page = -1
    st.session_state.zoom_level = 100
    st.session_state.keywords = []
    st.session_state.ttypes = []
    st.session_state.ppairs = []
    st.session_state["uploader_pdf_key"] = 1
    st.session_state["uploader_json_key"] = 1000
    st.session_state["parse_page"] = False

def load_json_state(file_content):
    try:
        save_data = json.loads(file_content)
        
        # First verify total pages match
        if (st.session_state.get('total_pages', 0) != 0 and 
            st.session_state.get('total_pages', 0) != save_data['total_pages']):
            st.error(f'JSON and PDF page number not match: {str(save_data["total_pages"])}:{str(st.session_state.get("total_pages", 0))}')
            return False
        
        #if "pages" not in st.session_state or len(st.session_state.pages) == 0:
            #st.session_state['pages'] = [{"page": x} for x in range(1, st.session_state.total_pages + 1)]

        # Restore basic session state
        for key, value in save_data.items():
            if key not in ['save_timestamp', "extraction_method", "cached_pages", "pages", "keywords", "ppairs", "ttypes", "book_index_edited", "keywords_edited", "types_edited", "pairs_edited"]:
                #setattr(st.session_state, key, value)
                st.session_state[key] = value
            if key == 'pages':
                #for p in save_data[key]:
                    #st.session_state.pages[p["page"] - 1] = p
                st.session_state["pages"] = save_data["pages"]
            if key == 'book_index_edited':
                if "edited_rows" in value and len(value["edited_rows"].items()) > 0:
                    print('hI tHeRe')
                    for item in value['edited_rows'].items():
                        print('-', item)
                        k, v = item
                        print(k, v)
                        for k2, v2 in v.items():
                            print("\t", k2, v2)
                            st.session_state["book_index"][int(k)][k2] = v2

            if key == 'keywords':
                print('right here')
                for kw in save_data[key]:
                    st.session_state[key].append(kw)
                if len(st.session_state[key]) == 0:
                    st.session_state[key].append('')
            if key == "keywords_edited":
                if "edited_rows" in value and len(value["edited_rows"].items()) > 0:
                    for item in value["edited_rows"].items():
                        print('-', item)
                        k, v = item
                        print(k, v)
                        for k2, v2 in v.items():
                            print("\t", k2, v2)
                            st.session_state["keywords"][int(k)] = v2
                            #s.session_state["keywords"].append()
                if "added_rows" in value and len(value["added_rows"]) > 0:
                    for item in value["added_rows"]:
                        for k2, v2 in item.items():
                            print('ADDED_ROW:', k2, v2)
                            st.session_state["keywords"].append(v2)
                st.session_state["keywords"] = [x for x in st.session_state["keywords"] if x not in ["", " ", None]]

            if key == 'ppairs':
                for kw in save_data[key]:
                    st.session_state[key].append(kw)
                if len(st.session_state[key]) == 0:
                    st.session_state[key].append('')
            if key == "pairs_edited":
                if "edited_rows" in value and len(value["edited_rows"].items()) > 0:
                    for item in value["edited_rows"].items():
                        print('-', item)
                        k, v = item
                        print(k, v)
                        for k2, v2 in v.items():
                            print("\t", k2, v2)
                            st.session_state["ppairs"][int(k)] = v2
                if "added_rows" in value and len(value["added_rows"]) > 0:
                    for item in value["added_rows"]:
                        for k2, v2 in item.items():
                            print('ADDED_ROW:', k2, v2)
                            st.session_state["ppairs"].append(v2)
                st.session_state["ppairs"] = [x for x in st.session_state["ppairs"] if x not in ["", " ", None]]
            
            if key == 'ttypes':
                for kw in save_data[key]:
                    st.session_state[key].append(kw)
                if len(st.session_state[key]) == 0:
                    st.session_state[key].append('')
            if key == "types_edited":
                if "edited_rows" in value and len(value["edited_rows"].items()) > 0:
                    for item in value["edited_rows"].items():
                        print('-', item)
                        k, v = item
                        print(k, v)
                        for k2, v2 in v.items():
                            print("\t", k2, v2)
                            st.session_state["ttypes"][int(k)] = v2
                if "added_rows" in value and len(value["added_rows"]) > 0:
                    for item in value["added_rows"]:
                        for k2, v2 in item.items():
                            print('ADDED_ROW:', k2, v2)
                            st.session_state["ttypes"].append(v2)
                st.session_state["ttypes"] = [x for x in st.session_state["ttypes"] if x not in ["", " ", None]]

            
        # Restore cached pages
        #if "cached_pages" in save_data:
            #for cache_key, cache_value in save_data["cached_pages"].items():
                #st.session_state[cache_key] = cache_value
        # Clear existing cached pages

        #keys_to_remove = [key for key in st.session_state.keys() if key.startswith("cached_page_")]
        #for key in keys_to_remove:
        #    del st.session_state[key]

        #for page in st.session_state.results:
        #    if st.session_state.page_num - 1  == page['page']:
        #        st.session_state[f"cached_page_{st.session_state.page_num-1}"] = page['text']
        #    elif st.session_state.page_num  == page['page']:
        #        st.session_state[f"cached_page_{st.session_state.page_num}"] = page['text']
                
        st.success(f"Session loaded successfully! (Saved on: {save_data['save_timestamp']})")
        return True
    except Exception as e:
        st.error(f"Error loading session state: {str(e)}")
        return False

def reindex_pages():
    last_section_index = None
    last_lesson_index = None
    for i, rec in enumerate(st.session_state['book_index']):
        if 'type' in rec and rec['type'] == 'chapter':
            if last_section_index:
                st.session_state['book_index'][last_section_index]['end_page'] = rec['start_page']
                st.session_state['book_index'][last_lesson_index]['end_page'] = rec['start_page']
            last_section_index = i
        elif 'type' in rec and rec['type'] == 'lesson':
            if last_lesson_index and "end_page" not in st.session_state['book_index'][last_lesson_index]:
                st.session_state['book_index'][last_lesson_index]['end_page'] = rec['start_page']
            last_lesson_index = i

    temp = pd.DataFrame(st.session_state['book_index'])
    for col_name in ['chapter', 'lesson', 'secnumber', 'secname', 'bnum', 'type', 'start_page', 'end_page']:
        if col_name not in temp:
            temp[col_name] = None

    st.session_state['book_index'] = temp.to_dict('records')
    

def main():
    st.set_page_config(layout="wide")

    # Initialize session states
    if 'page_num' not in st.session_state:
        st.session_state.page_num = 1
    if 'pages' not in st.session_state:
        st.session_state.pages = []
    if 'total_pages' not in st.session_state:
        st.session_state.total_pages = 0
    if 'first_human_page' not in st.session_state:
        st.session_state.first_human_page = -1
    if 'zoom_level' not in st.session_state:
        st.session_state.zoom_level = 100
    if 'keywords' not in st.session_state:
        st.session_state.keywords = []
    if 'ttypes' not in st.session_state:
        st.session_state.ttypes = []
    if 'ppairs' not in st.session_state:
        st.session_state.ppairs = []
    if "uploader_pdf_key" not in st.session_state:
        st.session_state["uploader_pdf_key"] = 1
    if "uploader_json_key" not in st.session_state:
        st.session_state["uploader_json_key"] = 1000
    if "parse_page" not in st.session_state:
        st.session_state["parse_page"] = False
    if 'book_index' not in st.session_state:
        st.session_state['book_index'] = []
    if 'is_json_loaded' not in st.session_state:
        st.session_state.is_json_loaded = False
    if 'showIndex' not in st.session_state:
        st.session_state.showIndex = False
    processor = get_processor()

    # Create the main navigation menu in the sidebar
    with st.sidebar:
        with st.expander("📁 File Operations", expanded=True):
            # Create tabs for different file operations
            file_tab1, file_tab2 = st.tabs(["Upload PDF", "Load JSON"])
            
            with file_tab1:
                uploaded_file = st.file_uploader(
                    "Choose a PDF file",
                    type="pdf",
                    key=st.session_state.get("uploader_pdf_key", 1)
                )
                
            with file_tab2:
                uploaded_json = st.file_uploader(
                    "Choose a saved session file",
                    type="json",
                    key=st.session_state.get("uploader_json_key", 1000)
                )
                if uploaded_json is not None and not st.session_state.is_json_loaded:
                    file_content = uploaded_json.read().decode('utf-8')
                    st.session_state.is_json_loaded = True
                    load_json_state(file_content)
                    #if load_json_state(file_content):
                        #st.rerun()

        st.markdown("---")
    st.title("PDF Content Extractor")
    
    
    def reset():
        #reset_session()
        #for key in st.session_state.keys():
            #del st.session_state[key]
        #processor = get_processor()
        st.session_state["uploader_pdf_key"] += 1
        st.session_state["uploader_json_key"] += 1
        #st.cache_data.clear()
        

        st.rerun()

    st.sidebar.button("New Project", on_click=reset)
    
    def parse():
        all_pages = process_pdf(processor, processor.temp_pdf_path, extraction_method)
        for page in all_pages:
            print(page)
            st.session_state.pages[page['page'] - 1][page["method"]] = page[extraction_method]
            del page["method"]

    def parse_page():
        #print('going to parse page', st.session_state.page_num)
        x = st.session_state.col_center if "col_center" in st.session_state else 0
        p = processor.parse_single_page(st.session_state.page_num, extraction_method, int(x))
        st.session_state.pages[st.session_state.page_num - 1][extraction_method] = p

    def remove_diacritics(txt):
        import re
        diacritics = ''.join([chr(x) for x in list(range(0x64b, 0x652)) + [1648, 1618]])
        return re.sub(' ?[' + diacritics + ']+', '', txt)

    def set_human_page():
        st.session_state.first_human_page = st.session_state.page_num
        print(st.session_state.first_human_page)

    with st.sidebar:
        with st.expander("Configuration:", expanded=False):
            #st.header("Configuration")
            extraction_methods = ["pdfplumber", "tesseract", "PyMuPDF", "surya"] #, "pdf2image/tesseract"]
            try:
                #import doctr
                #extraction_methods.extend(["doctr (OCR)", "All Methods"])
                pass
            except ImportError:
                pass
            
            extraction_method = st.radio("Select Extraction Method", extraction_methods)

            if extraction_method == "surya":
                st.number_input("2 col center X:", key="col_center")
            
            #uploaded_file = st.sidebar.file_uploader("Choose a PDF file", type="pdf", key=st.session_state["uploader_pdf_key"])

            pdf_page_number = processor.load_document(processor.temp_pdf_path)
            if st.session_state.total_pages != 0 and st.session_state.total_pages != pdf_page_number:
                st.error(f'JSON and PDF page number not match: {str(st.session_state.total_pages)}:{str(pdf_page_number)}')
            #    uploaded_file = None
            #else:
            #    st.session_state.total_pages = pdf_page_number

            if uploaded_file is not None:

                st.button("Parse All", on_click=parse)

                if st.session_state["parse_page"] or True:
                    st.button("Parse Page", on_click=parse_page)

                if st.button('Build Index'):
                    p = st.session_state[f"page_text_{st.session_state.page_num}"]
                    print('hi')
                    inx = processor.build_index(p)
                    st.session_state['book_index'] += inx
                    reindex_pages()
                if st.toggle("Show/Hide Index", value=st.session_state.showIndex, key="showIndex_key"):
                    print('st.session_state.showIndex: ', st.session_state.showIndex)
                    print('st.session_state.showIndex: ', st.session_state.showIndex_key)
                if st.session_state.pages:
                    st.button(
                        label="Set current page as 1st human page",
                        on_click=set_human_page
                    )
                    st.text('Current human page number: ' + str(st.session_state.page_num - st.session_state.first_human_page + 1 if (st.session_state.first_human_page > 0 and st.session_state.page_num - st.session_state.first_human_page >= 0) else -1))
                    st.text('First human page (offset): ' + str(st.session_state.first_human_page))
                    for page in st.session_state.pages:
                        page['human_page'] = page["page"] - st.session_state.first_human_page + 1 if (st.session_state.first_human_page != -1 and page["page"] - st.session_state.first_human_page >= 0) else -1
                else:
                    st.warning(f"No text extracted for page {st.session_state.page_num}")
                
                st.toggle("Show/Hide Markdown", value=st.session_state.showIndex, key="showMarkdown_key")

    if uploaded_file is not None:
        with st.sidebar:
            with st.expander("Edit:", expanded=False):
                if st.button('Remove diacritics'):
                    if "edited_text" in st.session_state.pages[st.session_state.page_num - 1]:
                        st.session_state.pages[st.session_state.page_num - 1]["edited_text"] = remove_diacritics(st.session_state.pages[st.session_state.page_num - 1]["edited_text"])
                    else:
                        st.session_state.pages[st.session_state.page_num - 1]["edited_text"] = remove_diacritics(st.session_state.pages[st.session_state.page_num - 1][extraction_method])
                st.text_input(label="To Replace:", placeholder="To replace", key="to_replace")
                st.text_input(label="Replace with:", placeholder="Replace with", key="replace_with")
                if st.button('Replace') and \
                    "to_replace" in st.session_state and st.session_state["to_replace"] != "" and \
                    "replace_with" in st.session_state:

                    if "edited_text" in st.session_state.pages[st.session_state.page_num - 1]:
                        st.session_state.pages[st.session_state.page_num - 1]["edited_text"] = st.session_state.pages[st.session_state.page_num - 1]["edited_text"].replace(st.session_state["to_replace"], st.session_state["replace_with"])
                    else:
                        st.session_state.pages[st.session_state.page_num - 1]["edited_text"] = st.session_state.pages[st.session_state.page_num - 1][extraction_method].replace(st.session_state["to_replace"], st.session_state["replace_with"])

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
            if len(st.session_state['pages']) == 0:
                st.session_state['pages'] = [{"page": x, "isData": True} for x in range(1, st.session_state.total_pages + 1)]
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
        
        is_data_key = f"is_data_page_{st.session_state.page_num}"
        is_data_page = st.session_state['pages'][st.session_state.page_num - 1]["isData"] if "isData" in st.session_state['pages'][st.session_state.page_num - 1] else False
        is_data = st.sidebar.toggle("Non-data / Data page", value=is_data_page , key=is_data_key)
        st.session_state['pages'][st.session_state.page_num - 1]["isData"] = is_data

        data_type_key = f"data_type_page_{st.session_state.page_num}"
        #data_type_page = st.session_state['pages'][st.session_state.page_num - 1]["dataType"] if "dataType" in st.session_state['pages'][st.session_state.page_num - 1] else False
        def set_data_type(key):
            if key in st.session_state:
                st.session_state['pages'][st.session_state.page_num - 1]["dataType"] = st.session_state[key]
        if is_data:
            if "dataType" in st.session_state['pages'][st.session_state.page_num - 1]:
                st.session_state[data_type_key] = st.session_state['pages'][st.session_state.page_num - 1]["dataType"]
            dataType = st.sidebar.selectbox("Type of data:", 
                ("context", "question", "answer", "context+question"), #context is default and no need to explicitly set in json data
                index=None,
                placeholder="Select data type",
                on_change=set_data_type, key=data_type_key, args=(data_type_key, )) #"question+answer", "cheat"
            print(dataType)

        to_review_key = f"to_reiew_page_{st.session_state.page_num}"
        to_review_page = st.session_state['pages'][st.session_state.page_num - 1]["toReview"] if "toReview" in st.session_state['pages'][st.session_state.page_num - 1] else False
        to_review = st.sidebar.toggle("Need Review", value=to_review_page , key=to_review_key)
        st.session_state['pages'][st.session_state.page_num - 1]["toReview"] = to_review

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
        
        def update_text(text_key):
            page_num = st.session_state.page_num
            new_text = st.session_state[text_key]
            
            # Always update the edited_texts dictionary when text changes
            st.session_state["pages"][page_num-1]["edited_text"] = new_text

        def get_current_page_text():
            page_key = f"{st.session_state.page_num}"

            if "edited_text" in st.session_state["pages"][st.session_state.page_num-1]:
                #st.session_state["parse_page"] = False
                return st.session_state["pages"][st.session_state.page_num-1]["edited_text"]

            if st.session_state.pages:
                for page in st.session_state.pages:
                    if page['page'] == st.session_state.page_num and extraction_method in page:
                        st.session_state["parse_page"] = False
                        return page[extraction_method]

            st.session_state["parse_page"] = True
            return "No text available"

        with right_col:
            #st.header(f"PDF Page {st.session_state.page_num}")
            st.subheader(f"PDF page {st.session_state.page_num}")
            
            if "showMarkdown_key" in st.session_state and st.session_state.showMarkdown_key:
                #if st.sidebar.toggle("Show/Hide Markdown", value=st.session_state.showIndex, key="showMarkdown_key"):
                to_md = """
                    <style>
                    .rtl {
                        direction: rtl;
                        text-align: right;
                    }
                    </style>
                """
                to_md += get_current_page_text().replace("\n", "<br>")
                st.markdown(to_md, unsafe_allow_html=True)
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
            #pix = page.get_pixmap()
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_bytes = pix.tobytes("png")

            # Convert image bytes to base64 for embedding in HTML
            img_base64 = base64.b64encode(img_bytes).decode()

            # Embed image in custom HTML with JavaScript for zoom control
            #custom_html = f""""""
            with open("custom_html.html",'r') as f: 
                custom_html = f.read()
            custom_html = custom_html.format(zoom_level=zoom_level, img_base64=img_base64)
            st.components.v1.html(custom_html, height=650, scrolling=False)

            #st.image(img_bytes, use_column_width=True)
        
        with left_col:
            #st.header("Extracted Text")
            st.subheader("Page text:")
            
            text_key = f"page_text_{st.session_state.page_num}"

            current_text = get_current_page_text()

            # Update session state with current text
            if text_key not in st.session_state:
                st.session_state[text_key] = current_text

            page_key = f"{st.session_state.page_num}"

            if "edited_text" in st.session_state["pages"][st.session_state.page_num-1]:
                # Show indicator that text has been edited
                st.info("This text has been edited. Changes are saved automatically.")

            if len(st.session_state['book_index']) > 0 and "showIndex_key" in st.session_state and st.session_state.showIndex_key:
                df = pd.DataFrame(st.session_state['book_index'])
                df = df[['chapter', 'lesson', 'secnumber', 'secname', 'type', 'start_page', 'end_page']]
                editor_text = st.data_editor(df, key="book_index_edited", use_container_width=False, height=(400 if len(df) < 20 else 800))
                #st.session_state['book_index'] = editor_text

            # Display the text area
            edited_text = st.text_area(
                f"Edit text if needed",
                value=current_text,
                key=text_key,
                #key="page_text_edited",
                on_change=update_text,
                args=(text_key,)
            )


        with st.sidebar:
            with st.expander("Keywords:", expanded=False):
                st.text('keywords:')
                if len(st.session_state.keywords) == 0:
                    addk = st.text_input('Add keyword')
                    if addk:
                        st.session_state["keywords"].append(addk)
                        st.rerun()
                keywords_text = st.data_editor(st.session_state.keywords, key="keywords_edited", use_container_width=True, num_rows="dynamic") #, hide_index=True)

                st.text("types:")
                if len(st.session_state.ttypes) == 0:
                    addt = st.text_input('Add type')
                    if addt:
                        st.session_state["ttypes"].append(addt)
                        st.rerun()
                types_text = st.data_editor(st.session_state.ttypes, key="types_edited", use_container_width=True, num_rows="dynamic") #, hide_index=True)

                st.text("pairs:")
                if len(st.session_state.ppairs) == 0:
                    addp = st.text_input('Add pair')
                    if addp:
                        st.session_state["ppairs"].append(addp)
                        st.rerun()
                pairs_text = st.data_editor(st.session_state.ppairs, key="pairs_edited", use_container_width=True, num_rows="dynamic") #, hide_index=True)


     # Load functionality
    #st.sidebar.markdown("---")
    #st.sidebar.subheader("Import JSON")
    #load_session_state()
    # Add debug information
    if os.getenv('DEBUG', 'False').lower() in ('true'):
        with st.expander("Debug Information", expanded=True):
            if len(st.session_state.pages) > 0:
                st.write('Current page: ', st.session_state.pages[st.session_state.page_num-1])
            st.write('keywords: ', st.session_state.keywords)
            if "keywords_edited" in st.session_state:
                st.write('keywords_edited: ', st.session_state.keywords_edited)
            st.write('pairs: ', st.session_state.ppairs)
            if "pairs_edited" in st.session_state:
                st.write('pairs_edited: ', st.session_state.pairs_edited)
            st.write('types: ', st.session_state.ttypes)
            if "types_edited" in st.session_state:
                st.write('types_edited: ', st.session_state.types_edited)
            st.write("SESSION: ", st.session_state)

if __name__ == "__main__":
    main()

# Keep the existing CSS styling
with open("css.html",'r') as f: 
    custom_css = f.read()
    st.markdown(custom_css, unsafe_allow_html=True)
