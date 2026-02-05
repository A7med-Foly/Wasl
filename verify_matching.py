from wasl_ai.src.matcher import match_resume_to_jobs

def verify():
    # Test connection to model
    print("Loading model and jobs...")
    
    # Simulate a parsed resume (Ahmed Foly's skills)
    resume_text = "Python Machine Learning Image Processing Computer Vision Data Mining TensorFlow Keras"
    
    print(f"\nMatching for skills: {resume_text}")
    print("-" * 50)
    
    matches = match_resume_to_jobs(resume_text, top_k=3)
    
    for i, m in enumerate(matches, 1):
        job = m['job']
        print(f"{i}. {job['title']} at {job['company']} (Score: {m['score']})")
        print(f"   Skills: {job['skills']}")
        print("-" * 50)

if __name__ == "__main__":
    verify()
