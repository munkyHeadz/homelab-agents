"""PostgreSQL database monitoring tools for health and performance tracking."""

import os
import psycopg
from crewai.tools import tool
from dotenv import load_dotenv
from typing import Optional
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# PostgreSQL configuration
POSTGRES_HOST = os.getenv('POSTGRES_HOST', '192.168.1.50')
POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', 5432))
POSTGRES_USER_AGENT = os.getenv('POSTGRES_USER_AGENT', 'agent_user')
POSTGRES_PASSWORD_AGENT = os.getenv('POSTGRES_PASSWORD_AGENT')


def _get_postgres_connection(database: str = 'postgres'):
    """
    Create PostgreSQL database connection.

    Args:
        database: Database name to connect to (default: postgres)

    Returns:
        psycopg connection object
    """
    return psycopg.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        user=POSTGRES_USER_AGENT,
        password=POSTGRES_PASSWORD_AGENT,
        dbname=database,
        connect_timeout=10
    )


@tool("Check PostgreSQL Health")
def check_postgres_health() -> str:
    """
    Check overall PostgreSQL server health and status.

    Returns:
        Health status including version, uptime, connection info, and basic metrics

    Use this tool to verify PostgreSQL is operational and get basic health metrics.
    """
    try:
        conn = _get_postgres_connection()
        cur = conn.cursor()

        # Get version
        cur.execute('SELECT version();')
        version = cur.fetchone()[0]
        pg_version = version.split(',')[0]

        # Get uptime
        cur.execute("SELECT NOW() - pg_postmaster_start_time() as uptime;")
        uptime = cur.fetchone()[0]
        uptime_str = str(uptime).split('.')[0]  # Remove microseconds

        # Get connection stats
        cur.execute("""
            SELECT
                count(*) as total_connections,
                count(*) FILTER (WHERE state = 'active') as active_connections,
                count(*) FILTER (WHERE state = 'idle') as idle_connections
            FROM pg_stat_activity;
        """)
        total_conn, active_conn, idle_conn = cur.fetchone()

        # Get max connections setting
        cur.execute("SHOW max_connections;")
        max_connections = int(cur.fetchone()[0])

        # Calculate connection usage percentage
        conn_usage = (total_conn / max_connections) * 100

        # Get database count
        cur.execute("SELECT count(*) FROM pg_database WHERE datistemplate = false;")
        db_count = cur.fetchone()[0]

        # Get cache hit ratio
        cur.execute("""
            SELECT
                round(sum(blks_hit) * 100.0 / nullif(sum(blks_hit) + sum(blks_read), 0), 2) as cache_hit_ratio
            FROM pg_stat_database;
        """)
        cache_hit_ratio = cur.fetchone()[0] or 0

        cur.close()
        conn.close()

        # Determine health status
        if conn_usage > 90:
            health_status = "🔴 CRITICAL"
        elif conn_usage > 75:
            health_status = "⚠️ WARNING"
        else:
            health_status = "✅ HEALTHY"

        result = f"""
=== PostgreSQL Server Health ===
Status: {health_status}

Version: {pg_version}
Uptime: {uptime_str}
Databases: {db_count}

Connections:
  Active: {active_conn}
  Idle: {idle_conn}
  Total: {total_conn}/{max_connections} ({conn_usage:.1f}% used)

Performance:
  Cache Hit Ratio: {cache_hit_ratio}% {'✓' if cache_hit_ratio > 90 else '⚠️'}
"""

        return result.strip()

    except psycopg.Error as e:
        return f"✗ PostgreSQL connection error: {e}"
    except Exception as e:
        return f"✗ Error checking PostgreSQL health: {str(e)}"


@tool("Query Database Performance")
def query_database_performance(show_queries: bool = False) -> str:
    """
    Analyze PostgreSQL database performance metrics.

    Args:
        show_queries: If True, show currently running queries (default: False)

    Returns:
        Performance metrics including active queries, locks, and slow queries

    Use this tool to identify performance issues, slow queries, and blocking locks.
    """
    try:
        conn = _get_postgres_connection()
        cur = conn.cursor()

        # Get long-running queries (>30 seconds)
        cur.execute("""
            SELECT
                pid,
                NOW() - query_start AS duration,
                state,
                LEFT(query, 80) as query
            FROM pg_stat_activity
            WHERE state != 'idle'
              AND query NOT LIKE '%pg_stat_activity%'
              AND NOW() - query_start > interval '30 seconds'
            ORDER BY duration DESC
            LIMIT 5;
        """)
        long_queries = cur.fetchall()

        # Get blocking locks
        cur.execute("""
            SELECT
                count(*) as blocked_queries
            FROM pg_stat_activity
            WHERE wait_event_type = 'Lock';
        """)
        blocked_count = cur.fetchone()[0]

        # Get transaction age
        cur.execute("""
            SELECT
                max(NOW() - xact_start) as max_transaction_age
            FROM pg_stat_activity
            WHERE state IN ('idle in transaction', 'active');
        """)
        max_tx_age = cur.fetchone()[0]

        # Get table bloat (approximate)
        cur.execute("""
            SELECT
                count(*) as total_tables,
                pg_size_pretty(sum(pg_total_relation_size(schemaname||'.'||tablename))) as total_size
            FROM pg_tables
            WHERE schemaname NOT IN ('pg_catalog', 'information_schema');
        """)
        table_count, total_size = cur.fetchone()

        # Get active queries if requested
        active_queries_str = ""
        if show_queries and long_queries:
            active_queries_str = "\n\nLong-Running Queries:"
            for pid, duration, state, query in long_queries:
                duration_str = str(duration).split('.')[0]
                active_queries_str += f"\n  PID {pid} ({duration_str}): {query}..."

        cur.close()
        conn.close()

        # Determine performance status
        if long_queries or blocked_count > 0:
            perf_status = "⚠️ ISSUES DETECTED"
        else:
            perf_status = "✅ GOOD"

        result = f"""
=== PostgreSQL Performance ===
Status: {perf_status}

Query Metrics:
  Long-Running Queries (>30s): {len(long_queries)}
  Blocked Queries: {blocked_count}
  Max Transaction Age: {str(max_tx_age).split('.')[0] if max_tx_age else 'None'}

Database Metrics:
  Tables: {table_count}
  Total Size: {total_size}
{active_queries_str}
"""

        return result.strip()

    except psycopg.Error as e:
        return f"✗ PostgreSQL connection error: {e}"
    except Exception as e:
        return f"✗ Error querying performance: {str(e)}"


@tool("Check Database Sizes")
def check_database_sizes() -> str:
    """
    Check sizes of all databases and identify largest tables.

    Returns:
        Database sizes sorted by size, and largest tables in each database

    Use this tool to monitor database growth and identify space usage issues.
    """
    try:
        conn = _get_postgres_connection()
        cur = conn.cursor()

        # Get all database sizes
        cur.execute("""
            SELECT
                datname,
                pg_size_pretty(pg_database_size(datname)) as size,
                pg_database_size(datname) as size_bytes
            FROM pg_database
            WHERE datistemplate = false
            ORDER BY size_bytes DESC;
        """)
        databases = cur.fetchall()

        # Get total size
        total_bytes = sum(db[2] for db in databases)
        total_size = databases[0][1] if databases else "0 bytes"

        # Get largest tables across all databases
        cur.execute("""
            SELECT
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
            FROM pg_tables
            WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
            ORDER BY size_bytes DESC
            LIMIT 5;
        """)
        largest_tables = cur.fetchall()

        cur.close()
        conn.close()

        # Format database list
        db_list = []
        for dbname, size, size_bytes in databases:
            percentage = (size_bytes / total_bytes * 100) if total_bytes > 0 else 0
            db_list.append(f"  {dbname}: {size} ({percentage:.1f}%)")

        # Format largest tables
        table_list = []
        for schema, table, size, _ in largest_tables:
            table_list.append(f"  {schema}.{table}: {size}")

        result = f"""
=== PostgreSQL Database Sizes ===

Databases ({len(databases)} total):
{chr(10).join(db_list)}

Largest Tables:
{chr(10).join(table_list) if table_list else '  None found'}
"""

        return result.strip()

    except psycopg.Error as e:
        return f"✗ PostgreSQL connection error: {e}"
    except Exception as e:
        return f"✗ Error checking database sizes: {str(e)}"


@tool("Monitor Database Connections")
def monitor_database_connections(database: Optional[str] = None) -> str:
    """
    Monitor active database connections and identify connection issues.

    Args:
        database: Optional specific database to monitor (default: all databases)

    Returns:
        Detailed connection information including active queries and idle connections

    Use this tool to troubleshoot connection pool issues or identify connection leaks.
    """
    try:
        conn = _get_postgres_connection()
        cur = conn.cursor()

        # Build query based on database filter
        db_filter = f"AND datname = '{database}'" if database else ""

        # Get connection breakdown by database and state
        cur.execute(f"""
            SELECT
                datname,
                state,
                count(*) as connection_count
            FROM pg_stat_activity
            WHERE datname IS NOT NULL {db_filter}
            GROUP BY datname, state
            ORDER BY datname, connection_count DESC;
        """)
        conn_breakdown = cur.fetchall()

        # Get connections by client
        cur.execute(f"""
            SELECT
                client_addr,
                count(*) as connections,
                count(*) FILTER (WHERE state = 'active') as active
            FROM pg_stat_activity
            WHERE datname IS NOT NULL {db_filter}
            GROUP BY client_addr
            ORDER BY connections DESC
            LIMIT 10;
        """)
        conn_by_client = cur.fetchall()

        # Get idle connection duration
        cur.execute(f"""
            SELECT
                count(*) as idle_connections,
                max(NOW() - state_change) as max_idle_time
            FROM pg_stat_activity
            WHERE state = 'idle'
              AND datname IS NOT NULL {db_filter};
        """)
        idle_count, max_idle = cur.fetchone()

        cur.close()
        conn.close()

        # Format connection breakdown
        breakdown_lines = []
        current_db = None
        for dbname, state, count in conn_breakdown:
            if dbname != current_db:
                breakdown_lines.append(f"\n{dbname}:")
                current_db = dbname
            breakdown_lines.append(f"  {state}: {count}")

        # Format client connections
        client_lines = []
        for client, total, active in conn_by_client:
            client_addr = client if client else "local"
            client_lines.append(f"  {client_addr}: {total} total, {active} active")

        max_idle_str = str(max_idle).split('.')[0] if max_idle else "0:00:00"

        result = f"""
=== PostgreSQL Connection Monitor ===

Connections by Database:{''.join(breakdown_lines)}

Connections by Client:
{chr(10).join(client_lines) if client_lines else '  None'}

Idle Connections:
  Count: {idle_count}
  Max Idle Time: {max_idle_str}
"""

        return result.strip()

    except psycopg.Error as e:
        return f"✗ PostgreSQL connection error: {e}"
    except Exception as e:
        return f"✗ Error monitoring connections: {str(e)}"


@tool("Check Specific Database")
def check_specific_database(database: str) -> str:
    """
    Get detailed information about a specific database.

    Args:
        database: Name of the database to check (e.g., 'agent_memory', 'n8n')

    Returns:
        Detailed database information including size, connections, and table count

    Use this tool to investigate issues with a specific database.
    """
    try:
        conn = _get_postgres_connection()
        cur = conn.cursor()

        # Check if database exists
        cur.execute("SELECT datname FROM pg_database WHERE datname = %s;", (database,))
        if not cur.fetchone():
            cur.close()
            conn.close()
            return f"✗ Database '{database}' not found"

        # Get database size
        cur.execute("SELECT pg_size_pretty(pg_database_size(%s));", (database,))
        db_size = cur.fetchone()[0]

        # Get connection count
        cur.execute("""
            SELECT count(*)
            FROM pg_stat_activity
            WHERE datname = %s;
        """, (database,))
        conn_count = cur.fetchone()[0]

        cur.close()
        conn.close()

        # Connect to specific database to get table info
        conn = _get_postgres_connection(database=database)
        cur = conn.cursor()

        # Get table count
        cur.execute("""
            SELECT count(*)
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema');
        """)
        table_count = cur.fetchone()[0]

        # Get largest tables in this database
        cur.execute("""
            SELECT
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
            FROM pg_tables
            WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            LIMIT 5;
        """)
        top_tables = cur.fetchall()

        # Get row counts for top tables
        table_info = []
        for tablename, size in top_tables:
            try:
                cur.execute(f"SELECT count(*) FROM {tablename};")
                row_count = cur.fetchone()[0]
                table_info.append(f"  {tablename}: {size} ({row_count:,} rows)")
            except:
                table_info.append(f"  {tablename}: {size}")

        cur.close()
        conn.close()

        result = f"""
=== Database: {database} ===

Size: {db_size}
Active Connections: {conn_count}
Tables: {table_count}

Largest Tables:
{chr(10).join(table_info) if table_info else '  None'}
"""

        return result.strip()

    except psycopg.Error as e:
        return f"✗ PostgreSQL connection error: {e}"
    except Exception as e:
        return f"✗ Error checking database '{database}': {str(e)}"
