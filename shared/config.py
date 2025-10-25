"""
Configuration loader for Homelab Agent System

Loads environment variables from .env file with validation and type conversion.
Provides centralized configuration access for all agents and MCP servers.
"""

import os
from pathlib import Path
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load .env file from project root
PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    print(f"Warning: {ENV_FILE} not found. Using environment variables only.")


class AnthropicConfig(BaseSettings):
    """Anthropic Claude API configuration"""
    api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    default_model: str = Field(default="claude-sonnet-4-20250514", alias="DEFAULT_MODEL")
    flagship_model: str = Field(default="claude-sonnet-4-5-20250929", alias="FLAGSHIP_MODEL")
    fast_model: str = Field(default="claude-3-5-haiku-20241022", alias="FAST_MODEL")


class PostgresConfig(BaseSettings):
    """PostgreSQL database configuration"""
    host: str = Field(..., alias="POSTGRES_HOST")
    port: int = Field(default=5432, alias="POSTGRES_PORT")

    # Databases
    db_memory: str = Field(default="agent_memory", alias="POSTGRES_DB_MEMORY")
    db_checkpoints: str = Field(default="agent_checkpoints", alias="POSTGRES_DB_CHECKPOINTS")
    db_n8n: str = Field(default="n8n", alias="POSTGRES_DB_N8N")

    # Users
    user_memory: str = Field(default="mem0_user", alias="POSTGRES_USER_MEMORY")
    password_memory: str = Field(..., alias="POSTGRES_PASSWORD_MEMORY")

    user_agent: str = Field(default="agent_user", alias="POSTGRES_USER_AGENT")
    password_agent: str = Field(..., alias="POSTGRES_PASSWORD_AGENT")

    user_n8n: str = Field(default="n8n_user", alias="POSTGRES_USER_N8N")
    password_n8n: str = Field(..., alias="POSTGRES_PASSWORD_N8N")

    def get_connection_string(self, db_name: str, user: str, password: str) -> str:
        """Generate PostgreSQL connection string"""
        return f"postgresql://{user}:{password}@{self.host}:{self.port}/{db_name}"

    @property
    def memory_dsn(self) -> str:
        return self.get_connection_string(self.db_memory, self.user_memory, self.password_memory)

    @property
    def checkpoints_dsn(self) -> str:
        return self.get_connection_string(self.db_checkpoints, self.user_agent, self.password_agent)

    @property
    def n8n_dsn(self) -> str:
        return self.get_connection_string(self.db_n8n, self.user_n8n, self.password_n8n)


class RedisConfig(BaseSettings):
    """Redis configuration"""
    host: str = Field(..., alias="REDIS_HOST")
    port: int = Field(default=6379, alias="REDIS_PORT")
    password: Optional[str] = Field(default=None, alias="REDIS_PASSWORD")

    @property
    def url(self) -> str:
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/0"
        return f"redis://{self.host}:{self.port}/0"


class TelegramConfig(BaseSettings):
    """Telegram bot configuration"""
    bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    chat_id: str = Field(..., alias="TELEGRAM_CHAT_ID")
    admin_ids: str = Field(..., alias="TELEGRAM_ADMIN_IDS")

    @property
    def admin_id_list(self) -> List[int]:
        """Parse comma-separated admin IDs"""
        return [int(id.strip()) for id in self.admin_ids.split(",") if id.strip()]


class ProxmoxConfig(BaseSettings):
    """Proxmox VE configuration"""
    host: str = Field(..., alias="PROXMOX_HOST")
    port: int = Field(default=8006, alias="PROXMOX_PORT")
    user: str = Field(default="root@pam", alias="PROXMOX_USER")
    password: str = Field(..., alias="PROXMOX_PASSWORD")
    node: str = Field(..., alias="PROXMOX_NODE")
    verify_ssl: bool = Field(default=False, alias="PROXMOX_VERIFY_SSL")

    # Optional: API token (more secure than password)
    token_id: Optional[str] = Field(default=None, alias="PROXMOX_TOKEN_ID")
    token_secret: Optional[str] = Field(default=None, alias="PROXMOX_TOKEN_SECRET")

    @property
    def url(self) -> str:
        return f"https://{self.host}:{self.port}/api2/json"


class N8nConfig(BaseSettings):
    """n8n workflow automation configuration"""
    host: str = Field(..., alias="N8N_HOST")
    port: int = Field(default=5678, alias="N8N_PORT")
    url: str = Field(..., alias="N8N_URL")
    basic_auth_user: str = Field(default="admin", alias="N8N_BASIC_AUTH_USER")
    basic_auth_password: str = Field(..., alias="N8N_BASIC_AUTH_PASSWORD")
    api_key: Optional[str] = Field(default=None, alias="N8N_API_KEY")


class PrometheusConfig(BaseSettings):
    """Prometheus monitoring configuration"""
    host: str = Field(default="localhost", alias="PROMETHEUS_HOST")
    port: int = Field(default=9090, alias="PROMETHEUS_PORT")
    url: str = Field(..., alias="PROMETHEUS_URL")


class GrafanaConfig(BaseSettings):
    """Grafana visualization configuration"""
    host: str = Field(default="localhost", alias="GRAFANA_HOST")
    port: int = Field(default=3000, alias="GRAFANA_PORT")
    url: str = Field(..., alias="GRAFANA_URL")
    api_key: Optional[str] = Field(default=None, alias="GRAFANA_API_KEY")


class AgentConfig(BaseSettings):
    """Agent behavior configuration"""
    autonomous_mode: bool = Field(default=True, alias="AGENT_AUTONOMOUS_MODE")
    require_human_approval: bool = Field(default=False, alias="AGENT_REQUIRE_HUMAN_APPROVAL")
    learning_enabled: bool = Field(default=True, alias="AGENT_LEARNING_ENABLED")
    learning_interval: str = Field(default="weekly", alias="AGENT_LEARNING_INTERVAL")

    confidence_threshold: float = Field(default=0.7, alias="AGENT_CONFIDENCE_THRESHOLD")
    risk_threshold: float = Field(default=0.8, alias="AGENT_RISK_THRESHOLD")

    memory_retention_days: int = Field(default=365, alias="AGENT_MEMORY_RETENTION_DAYS")
    memory_embedding_model: str = Field(default="text-embedding-3-small", alias="AGENT_MEMORY_EMBEDDING_MODEL")

    max_retries: int = Field(default=3, alias="AGENT_MAX_RETRIES")
    timeout_seconds: int = Field(default=300, alias="AGENT_TIMEOUT_SECONDS")


class LoggingConfig(BaseSettings):
    """Logging and observability configuration"""
    level: str = Field(default="INFO", alias="LOG_LEVEL")
    format: str = Field(default="json", alias="LOG_FORMAT")
    file: str = Field(default="/home/munky/homelab-agents/logs/agents.log", alias="LOG_FILE")

    metrics_enabled: bool = Field(default=True, alias="METRICS_ENABLED")
    metrics_port: int = Field(default=9100, alias="METRICS_PORT")


class SecurityConfig(BaseSettings):
    """Security and encryption configuration"""
    encryption_key: str = Field(..., alias="ENCRYPTION_KEY")
    jwt_secret: str = Field(..., alias="JWT_SECRET")
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_requests_per_minute: int = Field(default=60, alias="RATE_LIMIT_REQUESTS_PER_MINUTE")


class FeatureFlagsConfig(BaseSettings):
    """Feature flags for gradual rollout"""
    self_improvement: bool = Field(default=True, alias="FEATURE_SELF_IMPROVEMENT")
    auto_remediation: bool = Field(default=True, alias="FEATURE_AUTO_REMEDIATION")
    chaos_engineering: bool = Field(default=False, alias="FEATURE_CHAOS_ENGINEERING")
    predictive_scaling: bool = Field(default=False, alias="FEATURE_PREDICTIVE_SCALING")
    cost_optimization: bool = Field(default=True, alias="FEATURE_COST_OPTIMIZATION")


class UnifiConfig(BaseSettings):
    """Unifi Controller configuration

    Supports both Cloud API (recommended) and Local Controller API

    Cloud API (recommended):
        api_key: Your Unifi API key from console.ui.com
        site_id: Your site ID (found in console URL)
        use_cloud_api: Set to True (default)

    Local Controller API (legacy):
        host: Controller hostname or IP
        port: Controller port (default 443)
        username: Admin username
        password: Admin password
        site: Site name (default "default")
        use_cloud_api: Set to False
    """
    enabled: bool = Field(default=False, alias="UNIFI_ENABLED")

    # Cloud API settings (recommended)
    use_cloud_api: bool = Field(default=True, alias="UNIFI_USE_CLOUD_API")
    api_key: str = Field(default="", alias="UNIFI_API_KEY")
    site_id: str = Field(default="", alias="UNIFI_SITE_ID")

    # Local controller settings (legacy)
    host: str = Field(default="unifi.local", alias="UNIFI_HOST")
    port: int = Field(default=443, alias="UNIFI_PORT")
    username: str = Field(default="", alias="UNIFI_USERNAME")
    password: str = Field(default="", alias="UNIFI_PASSWORD")
    site: str = Field(default="default", alias="UNIFI_SITE")
    verify_ssl: bool = Field(default=False, alias="UNIFI_VERIFY_SSL")


class AdGuardConfig(BaseSettings):
    """AdGuard Home configuration"""
    enabled: bool = Field(default=False, alias="ADGUARD_ENABLED")
    host: str = Field(default="adguard.local", alias="ADGUARD_HOST")
    port: int = Field(default=80, alias="ADGUARD_PORT")
    username: str = Field(default="", alias="ADGUARD_USERNAME")
    password: str = Field(default="", alias="ADGUARD_PASSWORD")


class Config(BaseSettings):
    """Main configuration class aggregating all sub-configs"""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )

    # Environment
    environment: str = Field(default="production", alias="ENVIRONMENT")
    debug_mode: bool = Field(default=False, alias="DEBUG_MODE")
    dry_run: bool = Field(default=False, alias="DRY_RUN")

    # Timezone
    timezone: str = Field(default="Europe/Amsterdam", alias="TZ")

    # Sub-configurations
    anthropic: AnthropicConfig = Field(default_factory=AnthropicConfig)
    postgres: PostgresConfig = Field(default_factory=PostgresConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    proxmox: ProxmoxConfig = Field(default_factory=ProxmoxConfig)
    n8n: N8nConfig = Field(default_factory=N8nConfig)
    prometheus: PrometheusConfig = Field(default_factory=PrometheusConfig)
    grafana: GrafanaConfig = Field(default_factory=GrafanaConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    features: FeatureFlagsConfig = Field(default_factory=FeatureFlagsConfig)
    unifi: UnifiConfig = Field(default_factory=UnifiConfig)
    adguard: AdGuardConfig = Field(default_factory=AdGuardConfig)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    def validate_required_services(self) -> List[str]:
        """Check which required services are configured"""
        issues = []

        if not self.anthropic.api_key or "YOUR" in self.anthropic.api_key:
            issues.append("ANTHROPIC_API_KEY not set")

        if "192.168.1.XXX" in self.postgres.host:
            issues.append("POSTGRES_HOST not updated from default")

        if "YOUR" in self.telegram.bot_token:
            issues.append("TELEGRAM_BOT_TOKEN not set")

        if "YOUR" in self.proxmox.password:
            issues.append("PROXMOX_PASSWORD not set")

        return issues


# Singleton instance
config = Config()


# Convenience function for validation
def validate_config():
    """Validate configuration and print warnings"""
    issues = config.validate_required_services()

    if issues:
        print("⚠️  Configuration issues detected:")
        for issue in issues:
            print(f"  - {issue}")
        print("\nPlease update .env file with correct values.")
        return False

    print("✅ Configuration validated successfully")
    return True


if __name__ == "__main__":
    # Test configuration loading
    print("🔧 Homelab Agent System - Configuration Test\n")

    print(f"Environment: {config.environment}")
    print(f"Debug mode: {config.debug_mode}")
    print(f"Dry run: {config.dry_run}\n")

    print("Service Configurations:")
    print(f"  Anthropic API: {'✅' if config.anthropic.api_key and 'YOUR' not in config.anthropic.api_key else '❌'}")
    print(f"  PostgreSQL: {config.postgres.host}:{config.postgres.port}")
    print(f"  Redis: {config.redis.host}:{config.redis.port}")
    print(f"  Proxmox: {config.proxmox.host}:{config.proxmox.port}")
    print(f"  Telegram: {'✅' if 'YOUR' not in config.telegram.bot_token else '❌'}")
    print(f"  n8n: {config.n8n.url}\n")

    print("Agent Settings:")
    print(f"  Autonomous: {config.agent.autonomous_mode}")
    print(f"  Learning enabled: {config.agent.learning_enabled}")
    print(f"  Confidence threshold: {config.agent.confidence_threshold}")
    print(f"  Risk threshold: {config.agent.risk_threshold}\n")

    print("Feature Flags:")
    print(f"  Self-improvement: {config.features.self_improvement}")
    print(f"  Auto-remediation: {config.features.auto_remediation}")
    print(f"  Cost optimization: {config.features.cost_optimization}\n")

    # Validate
    validate_config()
