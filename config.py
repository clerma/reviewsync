from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Google
    google_service_account_json: Optional[str] = None
    google_location_id: Optional[str] = None
    google_account_id: Optional[str] = None

    # Facebook
    facebook_page_id: Optional[str] = None
    facebook_page_access_token: Optional[str] = None

    # Yelp
    yelp_api_key: Optional[str] = None
    yelp_business_id: Optional[str] = None

    # Notifications
    webhook_url: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    notify_email: Optional[str] = None

    # Auto-Responder
    auto_respond_enabled: bool = False
    auto_respond_min_rating: int = 4

    # Sync
    sync_interval_minutes: int = 60

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Data
    data_dir: str = "data"
    reviews_file: str = "data/reviews.json"

    # Jekyll Integration — path to your Jekyll _data/testimonial.yml
    testimonial_yml_path: Optional[str] = None

    # GitHub Integration — push testimonial.yml directly to your repo
    github_token: Optional[str] = None
    github_repo: str = "ohhsnap"  # owner/repo format, e.g., "carloslerma/ohhsnap"
    github_branch: str = "main"
    github_testimonial_path: str = "_data/testimonial.yml"  # path inside the repo

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
