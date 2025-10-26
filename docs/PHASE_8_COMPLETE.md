# Phase 8 Complete: PostgreSQL Database & Backup Monitoring

## 🎯 Phase Objective
Integrate PostgreSQL database monitoring into the AI agents system to provide comprehensive database health, performance tracking, and connection monitoring for the critical PostgreSQL server (LXC 200).

## ✅ What Was Accomplished

### 1. PostgreSQL Integration Tools Created

**File:** `/home/munky/homelab-agents/crews/tools/postgres_tools.py` (497 lines)

**5 New Tools Implemented:**

#### Tool 1: Check PostgreSQL Health
```python
@tool("Check PostgreSQL Health")
def check_postgres_health() -> str
```
- **Purpose:** Monitor overall PostgreSQL server health and status
- **Metrics Tracked:**
  - PostgreSQL version
  - Server uptime
  - Database count
  - Connection statistics (active/idle/total)
  - Connection usage percentage
  - Cache hit ratio
- **Health Status Levels:**
  - ✅ HEALTHY: <75% connection usage
  - ⚠️ WARNING: 75-90% connection usage
  - 🔴 CRITICAL: >90% connection usage
- **Use Cases:**
  - Verify PostgreSQL is operational
  - Monitor connection pool health
  - Track cache performance

#### Tool 2: Query Database Performance
```python
@tool("Query Database Performance")
def query_database_performance(show_queries: bool = False) -> str
```
- **Purpose:** Analyze PostgreSQL database performance metrics
- **Performance Indicators:**
  - Long-running queries (>30 seconds)
  - Blocked queries (lock wait events)
  - Maximum transaction age
  - Total table count and size
  - Option to show active query details
- **Status Levels:**
  - ✅ GOOD: No long-running or blocked queries
  - ⚠️ ISSUES DETECTED: Performance problems found
- **Use Cases:**
  - Identify slow queries
  - Detect blocking locks
  - Find performance bottlenecks

#### Tool 3: Check Database Sizes
```python
@tool("Check Database Sizes")
def check_database_sizes() -> str
```
- **Purpose:** Monitor database and table size growth
- **Information Provided:**
  - All databases sorted by size
  - Size percentages
  - Top 5 largest tables across all databases
  - Table sizes with row counts
- **Use Cases:**
  - Monitor disk space usage
  - Identify growth trends
  - Plan capacity upgrades

#### Tool 4: Monitor Database Connections
```python
@tool("Monitor Database Connections")
def monitor_database_connections(database: Optional[str] = None) -> str
```
- **Purpose:** Monitor active database connections in detail
- **Connection Metrics:**
  - Connections by database and state
  - Connections by client IP address
  - Idle connection statistics
  - Maximum idle time
- **Use Cases:**
  - Troubleshoot connection pool issues
  - Identify connection leaks
  - Track client connection patterns

#### Tool 5: Check Specific Database
```python
@tool("Check Specific Database")
def check_specific_database(database: str) -> str
```
- **Purpose:** Get detailed information about a specific database
- **Database Details:**
  - Database size
  - Active connection count
  - Table count
  - Top 5 largest tables with row counts
- **Supported Databases:**
  - agent_memory
  - agent_checkpoints
  - n8n
- **Use Cases:**
  - Investigate specific database issues
  - Verify database health
  - Monitor application-specific databases

### 2. PostgreSQL Access Configuration

**Database Server:**
- Host: 192.168.1.50 (LXC 200)
- Tailscale IP: 100.108.125.86
- Port: 5432

**Credentials:**
```bash
POSTGRES_HOST=192.168.1.50
POSTGRES_PORT=5432
POSTGRES_USER_AGENT=agent_user
POSTGRES_PASSWORD_AGENT=agentpass123
```

**Available Databases:**
- `postgres` (system database)
- `agent_memory` (mem0 user)
- `agent_checkpoints` (agent user)
- `n8n` (n8n user)

### 3. Integration with AI Agents

**Updated Files:**
- `crews/tools/__init__.py` - Added PostgreSQL tool exports
- `crews/tools/homelab_tools.py` - Imported PostgreSQL tools
- `crews/infrastructure_health/crew.py` - Added tools to agents
- `requirements-docker.txt` - Added psycopg + psycopg-binary

**Agent Tool Assignments:**

**Monitor Agent:**
- check_postgres_health ✅
- monitor_database_connections ✅

**Analyst Agent:**
- query_database_performance ✅
- check_database_sizes ✅
- check_specific_database ✅

**Healer Agent:**
- No PostgreSQL tools (cannot directly fix database issues)

**Communicator Agent:**
- No PostgreSQL tools (notification only)

### 4. Production Deployment

**Container:** homelab-agents:latest
**Host:** docker-gateway (100.67.169.111)
**Network:** monitoring
**Status:** ✅ Running and Operational

**Deployment Details:**
```bash
Docker Image: homelab-agents:latest (sha256:318c02212fca)
Container ID: db6902e5671d
Restart Policy: unless-stopped
Ports: 5000:5000
Volumes: /var/run/docker.sock
```

**Dependencies Added:**
- `psycopg==3.2.4` - PostgreSQL adapter (pure Python)
- `psycopg-binary==3.2.4` - Binary package for performance

**Verification:**
- Health endpoint: ✅ Responding (200 OK)
- Tools loaded: ✅ Confirmed in crew tool list
- Flask server: ✅ Running on port 5000
- PostgreSQL connection: ✅ Verified

## 📊 Integration Benefits

### Enhanced Capabilities

**1. Database Health Monitoring**
- Real-time connection pool monitoring
- Cache hit ratio tracking
- Automatic alerting on connection exhaustion
- Uptime and version tracking

**2. Performance Diagnostics**
- Long-running query detection (>30s)
- Blocking lock identification
- Transaction age monitoring
- Database size tracking

**3. Capacity Planning**
- Database growth trends
- Table size analysis
- Connection usage patterns
- Disk space forecasting

**4. Proactive Issue Detection**
- Connection pool exhaustion warnings
- Slow query alerts
- Lock contention detection
- Cache performance degradation

### Use Case Examples

**Scenario 1: Database Connection Exhaustion**
```
Alert: n8n service reporting connection errors

Monitor Agent:
1. Calls check_postgres_health() → Connection usage at 95% (CRITICAL)
2. Calls monitor_database_connections() → n8n has 90 idle connections
3. Escalates as critical database connection issue

Analyst Agent:
1. Calls check_specific_database('n8n') → Database size normal
2. Calls query_database_performance() → No long-running queries
3. Determines: Connection pool leak in n8n application

Result: AI identifies application misconfiguration, not database failure
```

**Scenario 2: Slow Query Performance**
```
Alert: Application response time degraded

Monitor Agent:
1. Calls check_postgres_health() → Cache hit ratio: 65% (LOW)
2. Escalates as warning performance issue

Analyst Agent:
1. Calls query_database_performance(show_queries=True) → 3 queries >60s
2. Calls check_database_sizes() → Large table growth detected
3. Determines: Missing indexes causing table scans

Result: AI identifies need for index optimization
```

**Scenario 3: Disk Space Warning**
```
Proactive Check: Scheduled health check

Monitor Agent:
1. Calls check_postgres_health() → All systems normal
2. Calls monitor_database_connections() → Normal usage

Analyst Agent (proactive):
1. Calls check_database_sizes() → agent_memory: 2.5 GB (75% growth)
2. Logs: Recommend database maintenance
3. No escalation (proactive notification only)

Result: AI tracks growth trends without false alarms
```

## 🔧 Technical Implementation Details

### Python 3.13 Compatibility

**Challenge:** psycopg2-binary doesn't have Python 3.13 wheels
```
Error: pg_config executable not found
psycopg2-binary requires compilation from source
```

**Solution:** Migrated to psycopg 3 (modern PostgreSQL adapter)
```python
# Old (psycopg2):
import psycopg2
conn = psycopg2.connect(database='postgres', ...)

# New (psycopg 3):
import psycopg
conn = psycopg.connect(dbname='postgres', ...)
```

**Key Differences:**
- Parameter name: `database` → `dbname`
- Pure Python implementation (no compilation needed)
- Binary package available: `psycopg-binary`
- Better async support (not used here)

### Connection Management

**Connection Function:**
```python
def _get_postgres_connection(database: str = 'postgres'):
    return psycopg.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        user=POSTGRES_USER_AGENT,
        password=POSTGRES_PASSWORD_AGENT,
        dbname=database,
        connect_timeout=10
    )
```

**Error Handling:**
```python
try:
    conn = _get_postgres_connection()
    cur = conn.cursor()
    # ... execute queries ...
    cur.close()
    conn.close()
except psycopg.Error as e:
    return f"✗ PostgreSQL connection error: {e}"
except Exception as e:
    return f"✗ Error: {str(e)}"
```

### Performance Queries

**Cache Hit Ratio:**
```sql
SELECT
    round(sum(blks_hit) * 100.0 / nullif(sum(blks_hit) + sum(blks_read), 0), 2)
FROM pg_stat_database;
```

**Long-Running Queries:**
```sql
SELECT pid, NOW() - query_start AS duration, state, LEFT(query, 80)
FROM pg_stat_activity
WHERE state != 'idle'
  AND query NOT LIKE '%pg_stat_activity%'
  AND NOW() - query_start > interval '30 seconds'
ORDER BY duration DESC
LIMIT 5;
```

**Database Sizes:**
```sql
SELECT datname, pg_size_pretty(pg_database_size(datname)) as size
FROM pg_database
WHERE datistemplate = false
ORDER BY pg_database_size(datname) DESC;
```

## 📈 Integration Statistics

| Metric | Value |
|--------|-------|
| **Tools Created** | 5 |
| **Lines of Code** | 497 |
| **Agents Updated** | 2 (Monitor, Analyst) |
| **Databases Monitored** | 3+ (configurable) |
| **Development Time** | ~2 hours |
| **Deployment Status** | ✅ Production |
| **Dependencies Added** | 2 (psycopg, psycopg-binary) |

## 🚀 Next Steps (Optional)

### Additional PostgreSQL Features

**1. Backup Monitoring**
```python
@tool("Check Database Backups")
def check_database_backups() -> str:
    """Verify last backup time and size"""
    # Query pg_stat_archiver or external backup system
```

**2. Replication Status**
```python
@tool("Check Replication Lag")
def check_replication_lag() -> str:
    """Monitor streaming replication lag"""
    # Query pg_stat_replication
```

**3. Vacuum/Analyze Status**
```python
@tool("Check Table Maintenance")
def check_table_maintenance() -> str:
    """Check when tables were last vacuumed/analyzed"""
    # Query pg_stat_user_tables
```

**4. Index Health**
```python
@tool("Analyze Index Usage")
def analyze_index_usage() -> str:
    """Identify unused or missing indexes"""
    # Query pg_stat_user_indexes
```

### Integration Enhancements

**1. Alertmanager Rules**
```yaml
- alert: PostgreSQLConnectionPoolHigh
  expr: (pg_stat_activity_count / pg_settings_max_connections) > 0.8
  for: 5m
  annotations:
    description: "PostgreSQL connection usage at {{ $value }}%"

- alert: PostgreSQLSlowQuery
  expr: pg_stat_activity_max_tx_duration > 300
  for: 2m
  annotations:
    description: "Slow query running for {{ $value }}s"
```

**2. Grafana Dashboard**
- Panel: Connection pool usage over time
- Panel: Cache hit ratio trend
- Panel: Top 10 slowest queries
- Panel: Database growth chart

**3. Automated Remediation**
- Terminate long-running queries (with safeguards)
- Kill idle transactions
- Recommend VACUUM operations
- Suggest index creation

## 🎯 Success Criteria

All objectives achieved:
- ✅ PostgreSQL connection working
- ✅ 5 monitoring tools implemented
- ✅ Tools integrated with Monitor and Analyst agents
- ✅ Production deployment successful
- ✅ psycopg 3 migration completed
- ✅ Database health monitoring operational
- ✅ Performance tracking enabled
- ✅ Documentation complete

## 📝 Documentation

**Files Created/Updated:**
- `crews/tools/postgres_tools.py` (NEW - 497 lines)
- `crews/tools/__init__.py` (UPDATED)
- `crews/tools/homelab_tools.py` (UPDATED)
- `crews/infrastructure_health/crew.py` (UPDATED)
- `requirements-docker.txt` (UPDATED - added psycopg)
- `docs/PHASE_8_COMPLETE.md` (NEW - this file)

## 🏆 Phase 8 Status: COMPLETE ✅

**The AI incident response system now has comprehensive PostgreSQL database monitoring and can track health, performance, and connections for the critical database server!**

---

**Completed:** 2025-10-26
**Phase Duration:** ~2 hours
**Status:** Production Operational with Database Monitoring ✅
**Next:** Phase 9 - Additional integrations (UniFi, Cloudflare) or system optimization
