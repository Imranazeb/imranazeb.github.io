from dotenv import load_dotenv
from anthropic import Anthropic
import os

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")

client = Anthropic(api_key=api_key) 