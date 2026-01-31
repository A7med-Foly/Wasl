import os
import json
import pdfplumber
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from typing import List, Optional

# Load environment variables
load_dotenv()


# Define Data Structure for LLM Output
class ResumeData(BaseModel):
    name: Optional[str] = Field(description="Full name of the candidate")
    email: Optional[str] = Field(description="Email address")
    phone: Optional[str] = Field(description="Phone number")
    skills: List[str] = Field(description="List of technical and soft skills")
    education: List[str] = Field(description="List of educational qualifications (Degree, University, Dates)")
    experience: List[str] = Field(description="List of work experiences (Role, Company, Dates, Description)")

def extract_text_from_pdf(pdf_path):
    """
    Extracts raw text from a PDF file.
    """
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return None
    return text

def parse_resume(text):
    """
    Parses resume text into a structured JSON format using OpenRouter.
    Requires OPENROUTER_API_KEY environment variable.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("WARNING: OPENROUTER_API_KEY not found. Returning empty structure.")
        return {
            "name": None, "email": None, "phone": None, 
            "skills": [], "education": [], "experience": [],
            "error": "Missing API Key"
        }

    # Initialize OpenRouter LLM (via LangChain OpenAI integration)
    # Using 'openai/gpt-4o-mini' as requested by user
    llm = ChatOpenAI(
        model="openai/gpt-4o-mini",
        temperature=0,
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1"
    )
    
    parser = JsonOutputParser(pydantic_object=ResumeData)
    
    prompt = PromptTemplate(
        template="""
        You are an expert Resume Parser. Extract the following information from the resume text provided below.
        Return the result as a valid JSON object matching the specified format. 
        Do not invent information. If a field is missing, leave it null or empty.
        
        Format instructions:
        {format_instructions}
        
        Resume Text:
        {text}
        """,
        input_variables=["text"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    chain = prompt | llm | parser
    
    try:
        result = chain.invoke({"text": text})
        return result
    except Exception as e:
        print(f"Error during LLM Parsing: {e}")
        return {
             "name": None, "email": None, "phone": None, 
            "skills": [], "education": [], "experience": [],
            "error": str(e)
        }


if __name__ == "__main__":
    # Test with a dummy file if run directly
    import sys
    import os
    
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        raw_text = extract_text_from_pdf(pdf_path)
        parsed_data = parse_resume(raw_text)
        print(json.dumps(parsed_data, indent=2))
    else:
        print("Usage: python parser.py <path_to_pdf>")
