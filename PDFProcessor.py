import pdfplumber
import fitz

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