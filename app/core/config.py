from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
        
    DATABASE_URL : str
    SUPABASE_ANON_KEY : str
    PROJECT_URL : str
    
    SECRET_KEY : str
    ALGORITHM : str='HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int=1000
    
    OTP_EXPIRE_MINUTES: int=10
    RESET_OTP_EXPIRE_MINUTES: int=10
    RESET_OTP_MAX_ATTEMPTS: int=20
    OTP_MAX_ATTEMPTS: int=20
    
    
    ADMIN_EMAIL: str
    ADMIN_PASSWORD: str
    
    EMAIL_HOST: str
    EMAIL_PORT: int=587
    EMAIL_SECURE: bool=False
    EMAIL_USER: str
    EMAIL_PASSWORD: str
    EMAIL_FROM: str
    
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str
    
    
    STRIPE_SECRET_KEY: str
    STRIPE_PUBLISHABLE_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    FRONTEND_URL: str
    
    class Config:
        env_file = '.env'
        
settings = Settings()
    