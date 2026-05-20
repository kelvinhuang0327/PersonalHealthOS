from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=('.env', '.env.local'), env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'Personal Health Platform API'
    app_env: str = 'dev'
    app_host: str = '0.0.0.0'
    app_port: int = 8000
    app_auto_create_tables: bool = True
    app_debug: bool = False
    log_level: str = 'INFO'
    trusted_hosts: str = '*'

    database_url: str = 'postgresql+psycopg2://postgres:postgres@localhost:5432/personal_health'

    jwt_secret_key: str = 'replace_me'
    jwt_algorithm: str = 'HS256'
    jwt_access_token_expire_minutes: int = 120

    s3_endpoint_url: str = 'http://localhost:9000'
    s3_access_key: str = 'minioadmin'
    s3_secret_key: str = 'minioadmin'
    s3_bucket: str = 'personal-health-docs'
    s3_region: str = 'us-east-1'
    storage_backend: str = 's3'
    local_storage_root: str = './uploads'

    max_upload_mb: int = 10
    allowed_mime_types: str = 'application/pdf,image/png,image/jpeg'
    allowed_file_extensions: str = 'pdf,png,jpg,jpeg'
    max_upload_filename_length: int = 200

    ai_provider: str = 'openai'
    openai_api_key: str = ''
    openai_model: str = 'gpt-4.1-mini'
    cors_allow_origins: str = 'http://localhost:3000,http://127.0.0.1:3000,http://localhost:3100,http://127.0.0.1:3100'
    cors_allow_methods: str = 'GET,POST,PUT,PATCH,DELETE,OPTIONS'
    cors_allow_headers: str = 'Authorization,Content-Type,Accept'
    cors_allow_credentials: bool = True
    rate_limit_enabled: bool = False
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60
    sentry_dsn: str = ''
    sentry_environment: str = 'production'

    ocr_language: str = 'eng'
    orchestrator_profile_path: str = 'runtime/agent_orchestrator/project_profile.json'
    orchestrator_scheduler_autostart: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
