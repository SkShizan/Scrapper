# config.py
import os
from dotenv import load_dotenv

# Find the .env file in the root directory
base_dir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(base_dir, '.env'))

class Config:
    """Base configuration class."""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_very_hard_to_guess_secret_string'
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Credentials
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
    GOOGLE_CX = os.environ.get('GOOGLE_CX')

    # Redis/RQ Settings
    REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
    QUEUES = ['high'] # We can add more, e.g., 'low'
    