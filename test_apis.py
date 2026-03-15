import os
from dotenv import load_dotenv
load_dotenv()

# Test Groq
try:
    from groq import Groq
    client = Groq(api_key=os.getenv('GROQ_API_KEY'))
    response = client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=[{'role': 'user', 'content': 'Say: Groq is working!'}],
        max_tokens=20
    )
    print('✅ GROQ:', response.choices[0].message.content)
except Exception as e:
    print('❌ GROQ ERROR:', str(e))

# Test Gemini
try:
    from google import genai
    gc = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
    r = gc.models.generate_content(
        model='models/gemini-2.5-pro',
        contents='Say: Gemini 2.5 Pro is working!'
    )
    print('✅ GEMINI:', r.text)
except Exception as e:
    print('❌ GEMINI ERROR:', str(e))