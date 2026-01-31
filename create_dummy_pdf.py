from reportlab.pdfgen import canvas

def create_dummy_resume(path):
    c = canvas.Canvas(path)
    c.drawString(100, 800, "John Doe")
    c.drawString(100, 780, "johndoe@example.com")
    c.drawString(100, 760, "123-456-7890")
    
    c.drawString(100, 720, "Skills:")
    c.drawString(120, 700, "- Python")
    c.drawString(120, 680, "- Machine Learning")
    c.drawString(120, 660, "- SQL")
    
    c.drawString(100, 620, "Education:")
    c.drawString(120, 600, "B.Sc. Computer Science, University of Technology")
    
    c.save()

if __name__ == "__main__":
    create_dummy_resume("wasl_ai/data/resumes/dummy_resume.pdf")
    print("Created dummy_resume.pdf")
