import sys
import os
from pypdf import PdfReader

def extract_text_from_pdf(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as e:
        return f"Error extracting {pdf_path}: {e}\n"

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python extract_pdf.py <output_txt_path> <pdf_path1> <pdf_path2> ...")
        sys.exit(1)
    
    output_path = sys.argv[1]
    pdf_paths = sys.argv[2:]
    
    with open(output_path, "w", encoding="utf-8") as f:
        for pdf_path in pdf_paths:
            if os.path.exists(pdf_path):
                f.write(f"--- Document: {os.path.basename(pdf_path)} ---\n")
                f.write(extract_text_from_pdf(pdf_path))
                f.write("\n\n")
            else:
                f.write(f"File not found: {pdf_path}\n\n")
    
    print(f"Extraction complete. Saved to {output_path}")
