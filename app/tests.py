from django.test import TestCase
import requests
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv

load_dotenv()

environemne =     os.getenv('APP_BASE_URL', 'http://localhost:8000').replace('http://', '').replace('https://', '').split('/')[0]

print(f"Environnement: {environemne}")