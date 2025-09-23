import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    POSTGRES_HOST = os.getenv("POSTGRES_HOST")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT")
    POSTGRES_USER = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_DB = os.getenv("POSTGRES_DB")

    TOKEN = os.getenv("TOKEN")
    ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
