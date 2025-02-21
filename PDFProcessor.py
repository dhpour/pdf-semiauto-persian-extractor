import pdfplumber
import fitz
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import numpy as np
import re
import string
from dotenv import load_dotenv
import os
from surya.ocr import run_ocr
from surya.model.detection.model import load_model as load_det_model, load_processor as load_det_processor
from surya.model.recognition.model import load_model as load_rec_model
from surya.model.recognition.processor import load_processor as load_rec_processor
import json
from google.genai import Client
from google.genai import types
import base64
from io import BytesIO

load_dotenv()

class PDFProcessor:
    def __init__(self):
        self.doctr_model = None
        self.temp_pdf_path = None
        self.doc = None
        self.latin_digits = "12345678900987654321"
        self.farsi_digits = "۱۲۳۴۵۶۷۸۹۰٠٩٨٧٦٥٤٣٢١"
        self.repl = str.maketrans(self.farsi_digits, self.latin_digits)
        self.langs = ["fa", "ar"] # Replace with your languages - optional but recommended
        self.gemini_client = Client(api_key=os.getenv("GOOGLE_API_KEY"))

    def load_surya(self):
        self.surya_det_processor, self.surya_det_model = load_det_processor(), load_det_model()
        self.surya_rec_model, self.surya_rec_processor = load_rec_model(), load_rec_processor()

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

    def reverse_match(self, match):
        return match.group(0)[::-1]
        
    def justifies_lefties(self, txt):
        new_txt = txt.translate(self.repl)
        new_txt = re.sub('[A-Za-z' + string.punctuation + ']+', self.reverse_match, new_txt)
        new_txt = re.sub(r'\d+', self.reverse_match, new_txt)
        return new_txt
    
    def build_index(self, txt):
        pattern = r'^(?P<number>\d+)\s+(?P<string1>.+?)(:\s+(?P<string2>.+))?$'
        lines = txt.split("\n")
        records = []
        for line in lines:
            tmp = {}
            match = re.match(pattern, line)
            if match:
                tmp['start_page'] = int(self.justifies_lefties(match.group("number")))
                tmp['secnumber'] = match.group("string1")
                if "فصل" in tmp['secnumber']:
                    tmp['type'] = 'chapter'
                    tmp['chapter'] = tmp['secnumber'].replace('فصل', '').strip()
                if "درس" in tmp['secnumber']:
                    tmp['type'] = 'lesson'
                    tmp['lesson'] = tmp['secnumber'].replace('درس', '').strip()
                tmp['secname'] = match.group("string2")
                records.append(tmp)
        return records

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
                "text": self.justifies_lefties(text) if text else "No text extracted"
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

    def process_with_pdf2image_tesseract(self, pdf_path):
        results = []
        pytesseract.pytesseract.tesseract_cmd = os.getenv('TESSER_ENGINE')
        pdf = convert_from_path(pdf_path, poppler_path=os.getenv('PDF2IMAGE_ENGINE'))
        for page_num in range(len(pdf)):
            text = pytesseract.image_to_string(pdf[page_num], lang='fas')
            results.append({
                "page": page_num + 1,
                "text": text if text else "No text extracted"
            })
        return results
    
    def process_with_tesseract(self, pdf_path):
        try:
            results = []
            pytesseract.pytesseract.tesseract_cmd = os.getenv('TESSER_ENGINE')

            for page_num in range(len(self.doc)):
                page = self.doc[page_num]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                
                # Convert PyMuPDF pixmap to PIL Image
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # Perform OCR
                text = pytesseract.image_to_string(img, lang='fas+ara')
                
                results.append({
                    "page": page_num + 1,
                    "text": text if text else "No text extracted"
                })
            return results
        except ImportError:
            return [{"page": 1, "text": "Tesseract is not installed. Install with: pip install pytesseract"}]
        except Exception as e:
            return [{"page": 1, "text": f"Error processing with Tesseract: {str(e)}"}]

    def parse_with_surya(self, pdf_path):
        all_pages = []
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            
            # Convert PyMuPDF pixmap to PIL Image
            all_lines = ''
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            predictions = run_ocr([img], [self.langs], self.surya_det_model, self.surya_det_processor, self.surya_rec_model, self.surya_rec_processor)
            for line in json.loads(predictions[0].json())['text_lines']:
                if line['bbox'][0] > 480: #right col
                    all_lines += line['text'] + "\n"
            for line in json.loads(predictions[0].json())['text_lines']:
                if line['bbox'][0] <= 480: #left col
                    all_lines += line['text'] + "\n"
            all_pages.append({
                'page': page_num + 1,
                'text': all_lines if all_lines != '' else "No text extracted"
            })
        return all_pages

    def gemini_single_page(self, page):
        p = self.doc[page]
        pix = p.get_pixmap(matrix=fitz.Matrix(2, 2))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        buffered = BytesIO()
        img.save(buffered, format="JPEG")
        img_bytes = buffered.getvalue()
    
        # Encode as base64
        encoded_image = base64.b64encode(img_bytes).decode('utf-8')

        # Convert PDF content to a format suitable for Gemini (bytes)
        contents = [
            types.Part.from_bytes(
                mime_type="image/jpeg",
                data=encoded_image
            ),
            "Extract all the text from this Image. Retain spaces between verses of poems with tab if needed. Just give the Image's content. No extra explanation is needed."
        ]
        response = self.gemini_client.models.generate_content(
            model=os.getenv("GEMINI_MODEL"),
            contents=contents
        )

        return response.text

    def parse_single_page(self, page, method, x=0):
        print('x: ', x)
        page = page - 1
        if method == "pdfplumber":
            with pdfplumber.open(self.temp_pdf_path) as pdf:
                return self.adjust_plumber_text(pdf.pages[page].extract_text())

        elif method == "PyMuPDF":
            p = self.doc[page]
            return self.justifies_lefties(p.get_text())

        elif method == "tesseract":
            pytesseract.pytesseract.tesseract_cmd = os.getenv('TESSER_ENGINE')
            p = self.doc[page]
            pix = p.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            return pytesseract.image_to_string(img, lang='fas+ara')
        
        elif method =="surya":
            p = self.doc[page]
            pix = p.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            predictions = run_ocr([img], [self.langs], self.surya_det_model, self.surya_det_processor, self.surya_rec_model, self.surya_rec_processor)
            all_lines = ''
            #with open('test.json', 'w', encoding='utf-8') as out:
                #out.write(predictions[0].json())
            for line in json.loads(predictions[0].json())['text_lines']:
                if line['bbox'][0] > x: #480: #right col
                    all_lines += line['text'] + "\n"
            for line in json.loads(predictions[0].json())['text_lines']:
                if line['bbox'][0] < x: #480: #left col
                    all_lines += line['text'] + "\n"
            return all_lines

        elif method=="gemini-2-flash": #"geminiflash2":
            return self.gemini_single_page(page)
    
    def cleanup(self):
        if self.doc:
            self.doc.close()
            self.doc = None
        if self.temp_pdf_path and os.path.exists(self.temp_pdf_path):
            try:
                os.remove(self.temp_pdf_path)
            except PermissionError:
                pass