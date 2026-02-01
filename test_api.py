import requests
import sys

def test_api():
    url = "http://localhost:8000/resume/parse"
    file_path = "data/resumes/CV2.pdf"
    
    print(f"Testing API at {url} with {file_path}...")
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(url, files=files)
            
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Response JSON:")
            print(response.json())
        else:
            print("Error:")
            print(response.text)
            
    except Exception as e:
        print(f"Failed to connect: {e}")
        print("Make sure the server is running: uvicorn wasl_ai.src.api:app --reload")

if __name__ == "__main__":
    test_api()
