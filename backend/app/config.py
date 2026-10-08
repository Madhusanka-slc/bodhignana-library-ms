import os


class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://library:library@db:5432/library")
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key-to-a-long-random-value")
    TOKEN_HOURS = int(os.getenv("TOKEN_HOURS", "12"))
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
    COVERS_DIR = os.getenv("COVERS_DIR", os.path.join(os.getcwd(), "data", "covers"))  # book cover pictures
    PHOTOS_DIR = os.getenv("PHOTOS_DIR", os.path.join(os.getcwd(), "data", "photos"))  # member photos


settings = Settings()
