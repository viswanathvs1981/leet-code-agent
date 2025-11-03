import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class AzureConfig:
    """Azure service configuration"""

    @property
    def cosmos_endpoint(self) -> Optional[str]:
        return os.getenv("AZURE_COSMOS_ENDPOINT")

    @property
    def cosmos_key(self) -> Optional[str]:
        return os.getenv("AZURE_COSMOS_KEY")

    @property
    def cosmos_database(self) -> str:
        return os.getenv("AZURE_COSMOS_DATABASE", "leetcode-agent")

    @property
    def storage_account(self) -> Optional[str]:
        return os.getenv("AZURE_STORAGE_ACCOUNT")

    @property
    def storage_key(self) -> Optional[str]:
        return os.getenv("AZURE_STORAGE_KEY")

    @property
    def storage_container(self) -> str:
        return os.getenv("AZURE_STORAGE_CONTAINER", "tutorials")


class OpenAIConfig:
    """OpenAI service configuration"""

    @property
    def api_key(self) -> Optional[str]:
        return os.getenv("OPENAI_API_KEY")

    @property
    def api_base(self) -> Optional[str]:
        return os.getenv("OPENAI_API_BASE")

    @property
    def deployment_name(self) -> str:
        return os.getenv("OPENAI_DEPLOYMENT_NAME", "gpt-4")

    @property
    def model(self) -> str:
        return os.getenv("OPENAI_MODEL", "gpt-4")


class LeetCodeConfig:
    """LeetCode crawling configuration"""

    @property
    def base_url(self) -> str:
        return os.getenv("LEETCODE_BASE_URL", "https://leetcode.com")

    @property
    def api_url(self) -> str:
        return os.getenv("LEETCODE_API_URL", "https://leetcode.com/api/problems/all/")


class AppConfig:
    """Application configuration"""

    @property
    def debug(self) -> bool:
        return os.getenv("DEBUG", "True").lower() == "true"

    @property
    def max_concurrent_requests(self) -> int:
        return int(os.getenv("MAX_CONCURRENT_REQUESTS", "5"))

    @property
    def cache_ttl_seconds(self) -> int:
        return int(os.getenv("CACHE_TTL_SECONDS", "3600"))


# Global configuration instances
azure_config = AzureConfig()
openai_config = OpenAIConfig()
leetcode_config = LeetCodeConfig()
app_config = AppConfig()
