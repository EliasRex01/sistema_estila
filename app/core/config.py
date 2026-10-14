from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./estila.db"
    JWT_SECRET: str = "changeme-jwt-estila"
    JWT_EXPIRE_MIN: int = 480
    MASTER_KEY: str = "changeme-master-estila"
    # Oracle ADB sin wallet (TLS): se arma oracle+oracledb con connect_args dsn.
    ORACLE_USER: str = ""
    ORACLE_PASSWORD: str = ""
    ORACLE_DSN: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
