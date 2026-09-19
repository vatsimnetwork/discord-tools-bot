from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    avwx_key: str = Field(repr=False)

    chartfox_key: str = Field(repr=False)

    discord_bot_token: str = Field(repr=False)

    events_channel_id: int | None = None
    exams_channel_id: int | None = None

    log_level: str = "INFO"

    network_broadcasts_channel_id: int | None = None

    network_kafka_group: str | None = None
    network_kafka_password: str = Field(default="", repr=False)
    network_kafka_server: str = ""
    network_kafka_username: str = ""

    screenshot_voting_channel_id: int | None = None
