"""
Configuration settings for Wasl AI using pydantic-settings.
Manages environment variables and centralizes LLM parameters.
"""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    OPENROUTER_API_KEY: str = Field(default="", validation_alias="OPENROUTER_API_KEY")
    LLM_MODEL: str = Field(default="openai/gpt-4o-mini", validation_alias="LLM_MODEL")
    LLM_BASE_URL: str = Field(default="https://openrouter.ai/api/v1", validation_alias="LLM_BASE_URL")
    
    # Module-specific temperatures
    PARSER_TEMPERATURE: float = Field(default=0.0, validation_alias="PARSER_TEMPERATURE")
    CAREER_ADVISOR_TEMPERATURE: float = Field(default=0.3, validation_alias="CAREER_ADVISOR_TEMPERATURE")
    LEARNING_PLANNER_TEMPERATURE: float = Field(default=0.2, validation_alias="LEARNING_PLANNER_TEMPERATURE")
    SKILL_ANALYZER_TEMPERATURE: float = Field(default=0.0, validation_alias="SKILL_ANALYZER_TEMPERATURE")

# Global settings instance
settings = Settings()
