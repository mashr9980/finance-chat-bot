import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = {
    "dbname": "chatbot_db",
    "user": "postgres",
    "password": "123",
    "host": "localhost",
    "port": "5432",
}

# Establish a database connection
def get_db_connection():
    return psycopg2.connect(**DATABASE_URL)