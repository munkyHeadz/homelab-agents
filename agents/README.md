# Autonomous Agents - Homelab Automation

This directory contains the autonomous agents that orchestrate homelab infrastructure using the MCP servers.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrator Agent                       │
│                    (LangGraph State Machine)                │
│  - Routes tasks to specialized agents                       │
│  - Coordinates multi-agent workflows                        │
│  - Handles human-in-the-loop approvals                      │
└──────────────┬──────────────┬──────────────┬────────────────┘
               │              │              │
       ┌───────▼──────┐  ┌────▼────┐  ┌─────▼──────┐
       │ Infrastructure│  │Monitoring│  │  Learning  │
       │     Agent     │  │  Agent   │  │   Agent    │
       └───────┬───────┘  └────┬─────┘  └─────┬──────┘
               │               │              │
    ┌──────────▼──────────┐ ┌──▼──────────────▼─────────┐
    │   MCP Servers       │ │    Mem0 Memory MCP        │
    │ - Proxmox           │ │  - Agent memories         │
    │ - Docker            │ │  - Pattern storage        │
    │ - Unifi             │ │  - Semantic search        │
    │ - Tailscale         │ └───────────────────────────┘
    │ - Cloudflare        │
    │ - Pi-hole           │
    └─────────────────────┘
```

## Agents

### 1. Orchestrator Agent (`orchestrator_agent.py`)

**Purpose:** Central coordinator using LangGraph for multi-agent workflows.

**Responsibilities:**
- Analyze user objectives and determine task type
- Route tasks to appropriate specialized agents
- Coordinate complex multi-step workflows
- Manage conversation state with PostgreSQL checkpointing
- Handle human approval requests
- Aggregate results from multiple agents

**Key Methods:**
- `execute(objective, thread_id)` - Execute an objective through the agent graph
- `resume(thread_id, approval_status)` - Resume after human approval

**State Machine:**
```
analyze_task → route_to_agent → execute_* → check_approval → aggregate_results
                                     ↓
                        (if approval needed: pause and wait)
```

**Model:** Claude Sonnet 4.5 (flagship) - Complex reasoning and coordination

**Example:**
```python
orchestrator = OrchestratorAgent()
result = await orchestrator.execute("Check all VMs and create backup if needed")
```

---

### 2. Infrastructure Agent (`infrastructure_agent.py`)

**Purpose:** Manage Proxmox VMs, LXC containers, and Docker infrastructure.

**Responsibilities:**
- VM/LXC lifecycle management
- Resource monitoring and optimization
- Automated scaling decisions
- Backup coordination
- Docker container orchestration

**MCP Servers Used:**
- Proxmox MCP (14 tools)
- Docker MCP (15 tools)
- Mem0 MCP (memory)

**Key Methods:**
- `execute(objective)` - Execute infrastructure task
- `monitor_resources()` - Continuous resource monitoring
- `optimize_resources()` - Analyze and recommend optimizations

**Model:** Claude Sonnet 4 (balanced) - Infrastructure decisions

**Example:**
```python
infra = InfrastructureAgent()
result = await infra.execute("Create LXC container for PostgreSQL")
```

---

### 3. Monitoring Agent (`monitoring_agent.py`)

**Purpose:** Network monitoring, alert analysis, and incident response.

**Responsibilities:**
- Network health monitoring (Unifi, Tailscale, Cloudflare)
- DNS management (Pi-hole, Cloudflare)
- Alert triage and analysis
- Automated incident response
- Security policy enforcement

**MCP Servers Used:**
- Unifi MCP (12 tools)
- Tailscale MCP (9 tools)
- Cloudflare MCP (10 tools)
- Pi-hole MCP (13 tools)
- Mem0 MCP (memory)

**Key Methods:**
- `execute(objective)` - Execute monitoring task
- `analyze_incident(alert_data)` - Analyze alerts and determine response
- `auto_remediate(incident_analysis)` - Automatically fix common issues

**Model:** Claude Sonnet 4 (balanced) - Incident analysis

**Example:**
```python
monitoring = MonitoringAgent()
result = await monitoring.analyze_incident({
    "alert_name": "HighCPU",
    "severity": "warning"
})
```

---

### 4. Learning Agent (`learning_agent.py`)

**Purpose:** Self-improvement through memory analysis and RLSR (Reinforcement Learning from Self Reward).

**Responsibilities:**
- Analyze past agent actions and outcomes
- Identify patterns and inefficiencies
- Generate improved strategies
- Update agent knowledge base
- Weekly performance reflection

**MCP Servers Used:**
- Mem0 MCP (8 tools)

**Key Methods:**
- `execute(objective)` - Execute learning task
- `analyze_past_performance(mem0)` - Identify patterns from history
- `generate_improvements(mem0)` - RLSR-based improvements
- `learn_from_incident(incident, resolution)` - Extract lessons
- `weekly_reflection()` - Automated weekly learning cycle

**Model:** Claude Sonnet 4.5 (flagship) - Complex analysis and creative insights

**RLSR Implementation:**
1. Agent reviews its own actions from memory
2. Assigns rewards to outcomes (self-evaluation)
3. Generates improved strategies
4. Updates decision policies

**Example:**
```python
learning = LearningAgent()
result = await learning.weekly_reflection()
```

---

## Running the Agent System

### Interactive Mode (CLI)

```bash
python run_agents.py --mode interactive
```

Provides a command-line interface for:
- Entering objectives manually
- Viewing system status
- Triggering learning cycles
- Browsing agent memories

**Commands:**
- `/help` - Show available commands
- `/status` - System status
- `/agents` - List all agents
- `/learn` - Run learning cycle
- `/quit` - Exit

### Daemon Mode (Background Service)

```bash
python run_agents.py --mode daemon
```

Runs continuously in the background:
- Monitors for tasks from n8n workflows
- Responds to Prometheus alerts
- Executes scheduled tasks
- Weekly learning cycle (Sundays at 2am)

### Single Objective Mode

```bash
python run_agents.py --mode single --objective "Check VM status"
```

Executes one task and exits. Useful for:
- Cron jobs
- n8n workflow integration
- One-off administrative tasks

### Direct Agent Access

```bash
python run_agents.py --agent infrastructure --objective "List all VMs"
```

Bypasses orchestrator and calls specific agent directly.

### Resume Workflow (Human Approval)

```bash
# Approve a pending task
python run_agents.py --thread-id thread_20250101_120000 --approve
```

Used when a task requires human approval and operator has reviewed it.

---

## Environment Configuration

### Required Environment Variables

```bash
# Anthropic API
ANTHROPIC_API_KEY=sk-ant-api03-...
DEFAULT_MODEL=claude-sonnet-4-20250514
FLAGSHIP_MODEL=claude-sonnet-4-5-20250929
FAST_MODEL=claude-3-5-haiku-20241022

# PostgreSQL (for checkpoints)
POSTGRES_HOST=192.168.1.XXX
POSTGRES_PORT=5432
POSTGRES_DB_CHECKPOINTS=agent_checkpoints
POSTGRES_USER_AGENT=agent_user
POSTGRES_PASSWORD_AGENT=your_password

# Agent behavior
AGENT_AUTONOMOUS_MODE=true
AGENT_REQUIRE_HUMAN_APPROVAL=false
AGENT_CONFIDENCE_THRESHOLD=0.7
AGENT_RISK_THRESHOLD=0.8
```

---

## LangGraph State Management

The orchestrator uses LangGraph with PostgreSQL checkpointing to maintain state across:
- Multiple conversation turns
- Human approval workflows
- Long-running multi-step tasks
- System restarts

**State Schema:**
```python
class AgentState(TypedDict):
    messages: Sequence[BaseMessage]
    task_type: str
    objective: str
    current_agent: str
    results: Dict[str, Any]
    requires_approval: bool
    approved: bool
    error: str | None
    iteration: int
```

**Checkpointing:** State is persisted to PostgreSQL after each node execution, allowing workflows to pause for human input and resume later.

---

## Human-in-the-Loop Approval

High-risk operations require human approval:

### Operations Requiring Approval:
- Deleting VMs or containers
- Modifying firewall rules
- Changing DNS settings
- Updating Tailscale ACLs
- Any destructive operation

### Approval Workflow:
1. Agent detects high-risk operation
2. Workflow pauses and sends Telegram notification (via n8n)
3. Human reviews and responds: `/approve` or `/reject`
4. Workflow resumes with decision

**Configuration:**
```bash
AGENT_REQUIRE_HUMAN_APPROVAL=true  # Always require approval
AGENT_RISK_THRESHOLD=0.8           # Auto-approve if risk < 0.8
```

---

## Cost Optimization

Agents use the LLMRouter to select appropriate models:

| Agent | Task Type | Model | Cost |
|-------|-----------|-------|------|
| Orchestrator | Complex coordination | Sonnet 4.5 | High |
| Infrastructure | Resource management | Sonnet 4 | Medium |
| Monitoring | Incident analysis | Sonnet 4 | Medium |
| Learning | Pattern analysis | Sonnet 4.5 | High |
| Simple queries | Status checks | Haiku | Low |

**Expected savings:** 70-80% compared to always using flagship model

---

## Memory and Learning

### Memory Storage (Mem0 + pgvector)

All agents store experiences in Mem0:
- **Infrastructure Agent:** Resource patterns, deployment outcomes
- **Monitoring Agent:** Incident resolutions, alert patterns
- **Learning Agent:** Insights, improvement recommendations

### Memory Retrieval

Agents use semantic search to recall relevant past experiences:

```python
# Search for similar past incidents
memories = await mem0.call_tool("search_memories", {
    "query": "high CPU usage on VM",
    "user_id": "monitoring_agent",
    "limit": 5
})
```

### Learning Cycles

**Daily:** Simple pattern recognition
**Weekly:** Full RLSR cycle with improvement generation
**Monthly:** Policy updates and knowledge base refresh

---

## Integration with n8n

Agents can be triggered from n8n workflows:

### Webhook Trigger
```javascript
// n8n HTTP Request node
POST http://localhost:5000/api/agents/execute
{
  "objective": "Check network health",
  "agent": "monitoring"
}
```

### Scheduled Tasks
- **Hourly:** Resource monitoring
- **Daily:** Backup verification
- **Weekly:** Learning reflection
- **Monthly:** Security audit

---

## Monitoring and Observability

### Structured Logging

All agents use structured logging:
```python
logger.info("Task executed",
    agent="infrastructure",
    objective="create_vm",
    success=True,
    duration_ms=1234
)
```

### Prometheus Metrics

Metrics exported on port 9100:
- `agent_task_total{agent, status}` - Task counts
- `agent_task_duration_seconds{agent}` - Execution time
- `agent_errors_total{agent}` - Error counts
- `mcp_tool_invocations_total{server, tool}` - MCP usage

### Grafana Dashboards

Pre-built dashboards for:
- Agent performance overview
- MCP server health
- Learning insights
- Incident response metrics

---

## Testing

### Unit Tests
```bash
cd /home/munky/homelab-agents
pytest tests/agents/
```

### Integration Tests
```bash
# Test each agent individually
python agents/infrastructure_agent.py
python agents/monitoring_agent.py
python agents/learning_agent.py
```

### End-to-End Test
```bash
python run_agents.py --mode single --objective "Check system health"
```

---

## Troubleshooting

### Agent Won't Start
```bash
# Check environment variables
cat .env | grep ANTHROPIC_API_KEY

# Verify database connection
psql -h $POSTGRES_HOST -U $POSTGRES_USER_AGENT -d $POSTGRES_DB_CHECKPOINTS

# Check MCP servers
python mcp_servers/proxmox_mcp/server.py
```

### Task Execution Fails
```bash
# Check logs
tail -f logs/agents.log

# Enable debug mode
LOG_LEVEL=DEBUG python run_agents.py --mode interactive
```

### Memory Errors
```bash
# Verify Mem0 MCP connection
python mcp_servers/mem0_mcp/server.py

# Check PostgreSQL pgvector extension
psql -h $POSTGRES_HOST -U $POSTGRES_USER_MEMORY -d $POSTGRES_DB_MEMORY -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

---

## Next Steps

1. **Deploy PostgreSQL with pgvector** (see QUICK_START.md)
2. **Configure environment variables** (copy .env.example to .env)
3. **Test MCP servers** individually
4. **Run in interactive mode** to test basic functionality
5. **Set up n8n workflows** for Telegram integration
6. **Deploy as systemd service** for daemon mode

---

## Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [Mem0 Documentation](https://docs.mem0.ai/)
- [Master Plan](../HOMELAB_AUTOMATION_MASTER_PLAN.md)
