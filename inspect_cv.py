from wasl_ai.src.parser import extract_text_from_pdf

text = extract_text_from_pdf('data/resumes/CV2.pdf')
with open('cv_text2.txt', 'w') as f:
    f.write(text)
print("Text saved to cv_text2.txt")
