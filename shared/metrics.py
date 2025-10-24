"""
Prometheus metrics for homelab agents
"""

from prometheus_client import Counter, Gauge, Histogram, generate_latest, REGISTRY
from prometheus_client import start_http_server
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Agent execution metrics
agent_tasks_total = Counter(
    'agent_tasks_total',
    'Total number of tasks executed by agents',
    ['agent_name', 'status']
)

agent_task_duration_seconds = Histogram(
    'agent_task_duration_seconds',
    'Duration of agent task execution',
    ['agent_name', 'task_type']
)

agent_errors_total = Counter(
    'agent_errors_total',
    'Total number of errors encountered by agents',
    ['agent_name', 'error_type']
)

# MCP server connection metrics
mcp_connections_active = Gauge(
    'mcp_connections_active',
    'Number of active MCP server connections',
    ['agent_name', 'mcp_server']
)

mcp_requests_total = Counter(
    'mcp_requests_total',
    'Total number of MCP requests',
    ['agent_name', 'mcp_server', 'tool_name', 'status']
)

mcp_request_duration_seconds = Histogram(
    'mcp_request_duration_seconds',
    'Duration of MCP requests',
    ['agent_name', 'mcp_server', 'tool_name']
)

# Infrastructure metrics
infrastructure_vms_total = Gauge(
    'infrastructure_vms_total',
    'Total number of VMs',
    ['status']
)

infrastructure_containers_total = Gauge(
    'infrastructure_containers_total',
    'Total number of Docker containers',
    ['status']
)

# Telegram bot metrics
telegram_messages_received_total = Counter(
    'telegram_messages_received_total',
    'Total number of Telegram messages received',
    ['command_type']
)

telegram_messages_sent_total = Counter(
    'telegram_messages_sent_total',
    'Total number of Telegram messages sent',
    ['message_type']
)

telegram_command_duration_seconds = Histogram(
    'telegram_command_duration_seconds',
    'Duration of Telegram command processing',
    ['command']
)

# System health metrics
agent_health_status = Gauge(
    'agent_health_status',
    'Health status of agent (1=healthy, 0=unhealthy)',
    ['agent_name']
)

agent_last_execution_timestamp = Gauge(
    'agent_last_execution_timestamp',
    'Timestamp of last agent execution',
    ['agent_name']
)


class MetricsServer:
    """HTTP server for exposing Prometheus metrics"""

    def __init__(self, port: int = 8000):
        self.port = port
        self.server = None

    def start(self):
        """Start the metrics HTTP server"""
        try:
            start_http_server(self.port)
            logger.info(f"Metrics server started on port {self.port}")
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")
            raise

    @staticmethod
    def get_metrics() -> bytes:
        """Get current metrics in Prometheus format"""
        return generate_latest(REGISTRY)


class MetricsCollector:
    """Helper class for collecting metrics in agents"""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name

    def record_task_start(self, task_type: str):
        """Record the start of a task"""
        agent_last_execution_timestamp.labels(agent_name=self.agent_name).set(time.time())

    def record_task_success(self, task_type: str, duration: float):
        """Record successful task completion"""
        agent_tasks_total.labels(agent_name=self.agent_name, status='success').inc()
        agent_task_duration_seconds.labels(agent_name=self.agent_name, task_type=task_type).observe(duration)
        agent_health_status.labels(agent_name=self.agent_name).set(1)

    def record_task_failure(self, task_type: str, error_type: str):
        """Record task failure"""
        agent_tasks_total.labels(agent_name=self.agent_name, status='failure').inc()
        agent_errors_total.labels(agent_name=self.agent_name, error_type=error_type).inc()

    def record_mcp_connection(self, mcp_server: str, active: bool):
        """Record MCP connection status"""
        mcp_connections_active.labels(
            agent_name=self.agent_name,
            mcp_server=mcp_server
        ).set(1 if active else 0)

    def record_mcp_request(self, mcp_server: str, tool_name: str, duration: float, success: bool):
        """Record MCP request"""
        status = 'success' if success else 'failure'
        mcp_requests_total.labels(
            agent_name=self.agent_name,
            mcp_server=mcp_server,
            tool_name=tool_name,
            status=status
        ).inc()
        mcp_request_duration_seconds.labels(
            agent_name=self.agent_name,
            mcp_server=mcp_server,
            tool_name=tool_name
        ).observe(duration)

    def set_health_status(self, healthy: bool):
        """Set agent health status"""
        agent_health_status.labels(agent_name=self.agent_name).set(1 if healthy else 0)


# Global metrics server instance
_metrics_server: Optional[MetricsServer] = None


def start_metrics_server(port: int = 8000):
    """Start the global metrics server"""
    global _metrics_server
    if _metrics_server is None:
        _metrics_server = MetricsServer(port)
        _metrics_server.start()
    return _metrics_server


def get_metrics_collector(agent_name: str) -> MetricsCollector:
    """Get a metrics collector for an agent"""
    return MetricsCollector(agent_name)
