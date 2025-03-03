import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "your-secret-key"
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    TEMPLATES_AUTO_RELOAD = True
