from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"

    # PMS API
    PMS_BASE_URL: str = "https://pmsapidev.visioncollab.com"
    PMS_EMAIL: str
    PMS_PASSWORD: str
    PMS_PROJECT_ID: int = 844
    PMS_MILESTONE_ID: str = "1209"
    PMS_ORGANIZATION_ID: str = "80b34e4b-d16e-45b5-961a-883c02409c24"
    PMS_USER_ID: int = 797
    PMS_DEFAULT_BOARD_ID: int = 2011
    PMS_DEFAULT_BOARD_TYPE_ID: int = 5
    PMS_DEFAULT_TASK_TYPE_ID: int = 35
    PMS_DEFAULT_SEVERITY_ID: int = 1

    # Workflow column classification (keyword-based; IDs vary per project)
    PMS_DONE_BOARD_KEYWORDS: str = "done,completed,complete,closed,finished"
    PMS_IN_PROGRESS_BOARD_KEYWORDS: str = "in progress,in-progress,inprogress"
    PMS_DONE_BOARD_IDS: str = ""
    PMS_IN_PROGRESS_BOARD_IDS: str = ""

    # Server
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    WHATSAPP_VERIFY_TOKEN: str = "change-me"
    META_ACCESS_TOKEN: str
    PHONE_NUMBER_ID: str
    WHATSAPP_BUSINESS_ACCOUNT_ID: str

    # Database
    DATABASE_URL: str
    SCHEMA_NAME: str = "public"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
