import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Supabase default transaction mode is often pooling, but psycopg2 works fine with it.
