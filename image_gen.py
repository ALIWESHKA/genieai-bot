import requests
import tempfile
import os

def generate_image(prompt: str) -> str:
    url = f"https://image.pollinations.ai/prompt/{prompt}?width=1024&height=1024&nologo=true"
    
    response = requests.get(url, timeout=120, stream=True)
    
    if response.status_code == 200:
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, "temp_image.png")
        
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return file_path
    else:
        raise Exception(f"Image generation failed: {response.status_code}")
