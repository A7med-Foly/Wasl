import sys
import json
import os
from src.parser import extract_text_from_pdf, parse_resume
from reportlab.pdfgen import canvas

def create_dummy_resume_if_not_exists(path):
    if os.path.exists(path):
        return
    
    print(f"Creating dummy resume at {path}...")
    c = canvas.Canvas(path)
    c.drawString(100, 800, "John Doe")
    c.drawString(100, 780, "johndoe@example.com")
    c.drawString(100, 760, "123-456-7890")
    
    c.drawString(100, 720, "Skills:")
    c.drawString(120, 700, "- Python")
    c.drawString(120, 680, "- Machine Learning")
    c.drawString(120, 660, "- SQL")
    c.drawString(120, 640, "- Git")
    
    c.drawString(100, 600, "Education:")
    c.drawString(120, 580, "B.Sc. Computer Science, University of Technology")
    
    c.save()

def main():
    pdf_path = "data/resumes/CV2.pdf"
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    
    create_dummy_resume_if_not_exists(pdf_path)
    
    print(f"Parsing resume: {pdf_path}")
    raw_text = extract_text_from_pdf(pdf_path)
    
    if raw_text:
        print("\n--- Extracted Text ---")
        print(raw_text.strip())
        print("----------------------\n")
        
        parsed_data = parse_resume(raw_text)
        print("--- Parsed JSON Data ---")
        print(json.dumps(parsed_data, indent=2))
        print("------------------------")
    else:
        print("Failed to extract text.")

if __name__ == "__main__":
    main()
