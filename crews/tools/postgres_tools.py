"""PostgreSQL database monitoring tools for health and performance tracking."""

import os
from datetime import datetime, timedelta
from typing import Optional

import psycopg
from crewai.tools import tool
from dotenv import load_dotenv

from crews.approval import get_approval_manager

# Load environment variables
load_dotenv()

# PostgreSQL configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "192.168.1.50")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", 5432))
POSTGRES_USER_AGENT = os.getenv("POSTGRES_USER_AGENT", "agent_user")
POSTGRES_PASSWORD_AGENT = os.getenv("POSTGRES_PASSWORD_AGENT")


def _get_postgres_connection(database: str = "postgres"):
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
        connect_timeout=10,
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
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        pg_version = version.split(",")[0]

        # Get uptime
        cur.execute("SELECT NOW() - pg_postmaster_start_time() as uptime;")
        uptime = cur.fetchone()[0]
        uptime_str = str(uptime).split(".")[0]  # Remove microseconds

        # Get connection stats
        cur.execute(
            """
            SELECT
                count(*) as total_connections,
                count(*) FILTER (WHERE state = 'active') as active_connections,
                count(*) FILTER (WHERE state = 'idle') as idle_connections
            FROM pg_stat_activity;
        """
        )
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
        cur.execute(
            """
            SELECT
                round(sum(blks_hit) * 100.0 / nullif(sum(blks_hit) + sum(blks_read), 0), 2) as cache_hit_ratio
            FROM pg_stat_database;
        """
        )
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
        cur.execute(
            """
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
        """
        )
        long_queries = cur.fetchall()

        # Get blocking locks
        cur.execute(
            """
            SELECT
                count(*) as blocked_queries
            FROM pg_stat_activity
            WHERE wait_event_type = 'Lock';
        """
        )
        blocked_count = cur.fetchone()[0]

        # Get transaction age
        cur.execute(
            """
            SELECT
                max(NOW() - xact_start) as max_transaction_age
            FROM pg_stat_activity
            WHERE state IN ('idle in transaction', 'active');
        """
        )
        max_tx_age = cur.fetchone()[0]

        # Get table bloat (approximate)
        cur.execute(
            """
            SELECT
                count(*) as total_tables,
                pg_size_pretty(sum(pg_total_relation_size(schemaname||'.'||tablename))) as total_size
            FROM pg_tables
            WHERE schemaname NOT IN ('pg_catalog', 'information_schema');
        """
        )
        table_count, total_size = cur.fetchone()

        # Get active queries if requested
        active_queries_str = ""
        if show_queries and long_queries:
            active_queries_str = "\n\nLong-Running Queries:"
            for pid, duration, state, query in long_queries:
                duration_str = str(duration).split(".")[0]
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
        cur.execute(
            """
            SELECT
                datname,
                pg_size_pretty(pg_database_size(datname)) as size,
                pg_database_size(datname) as size_bytes
            FROM pg_database
            WHERE datistemplate = false
            ORDER BY size_bytes DESC;
        """
        )
        databases = cur.fetchall()

        # Get total size
        total_bytes = sum(db[2] for db in databases)
        total_size = databases[0][1] if databases else "0 bytes"

        # Get largest tables across all databases
        cur.execute(
            """
            SELECT
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
            FROM pg_tables
            WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
            ORDER BY size_bytes DESC
            LIMIT 5;
        """
        )
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
        cur.execute(
            f"""
            SELECT
                datname,
                state,
                count(*) as connection_count
            FROM pg_stat_activity
            WHERE datname IS NOT NULL {db_filter}
            GROUP BY datname, state
            ORDER BY datname, connection_count DESC;
        """
        )
        conn_breakdown = cur.fetchall()

        # Get connections by client
        cur.execute(
            f"""
            SELECT
                client_addr,
                count(*) as connections,
                count(*) FILTER (WHERE state = 'active') as active
            FROM pg_stat_activity
            WHERE datname IS NOT NULL {db_filter}
            GROUP BY client_addr
            ORDER BY connections DESC
            LIMIT 10;
        """
        )
        conn_by_client = cur.fetchall()

        # Get idle connection duration
        cur.execute(
            f"""
            SELECT
                count(*) as idle_connections,
                max(NOW() - state_change) as max_idle_time
            FROM pg_stat_activity
            WHERE state = 'idle'
              AND datname IS NOT NULL {db_filter};
        """
        )
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

        max_idle_str = str(max_idle).split(".")[0] if max_idle else "0:00:00"

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
        cur.execute(
            """
            SELECT count(*)
            FROM pg_stat_activity
            WHERE datname = %s;
        """,
            (database,),
        )
        conn_count = cur.fetchone()[0]

        cur.close()
        conn.close()

        # Connect to specific database to get table info
        conn = _get_postgres_connection(database=database)
        cur = conn.cursor()

        # Get table count
        cur.execute(
            """
            SELECT count(*)
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema');
        """
        )
        table_count = cur.fetchone()[0]

        # Get largest tables in this database
        cur.execute(
            """
            SELECT
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
            FROM pg_tables
            WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            LIMIT 5;
        """
        )
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


@tool("Check Replication Status")
def check_replication_status() -> str:
    """
    Check PostgreSQL replication status and lag.

    Returns:
        Replication status, lag times, and replica health

    Use Cases:
        - Monitor replication lag
        - Verify replica synchronization
        - Detect replication failures
        - Capacity planning for replicas
    """
    try:
        conn = _get_postgres_connection()
        cursor = conn.cursor()

        # Check if this is a primary or replica
        cursor.execute("SELECT pg_is_in_recovery();")
        is_replica = cursor.fetchone()[0]

        output = ["=== PostgreSQL Replication Status ==="]

        if is_replica:
            output.append("Role: Replica (Standby)")
            output.append("")

            # Get replica lag
            cursor.execute(
                """
                SELECT 
                    CASE WHEN pg_last_wal_receive_lsn() = pg_last_wal_replay_lsn()
                        THEN 0
                        ELSE EXTRACT(EPOCH FROM now() - pg_last_xact_replay_timestamp())
                    END AS lag_seconds,
                    pg_last_wal_receive_lsn(),
                    pg_last_wal_replay_lsn(),
                    pg_last_xact_replay_timestamp();
            """
            )

            lag_info = cursor.fetchone()
            if lag_info:
                lag_seconds = lag_info[0] if lag_info[0] else 0
                last_replay = lag_info[3]

                output.append(f"Replication Lag: {lag_seconds:.2f} seconds")
                output.append(f"Last Transaction Replay: {last_replay}")

                if lag_seconds > 10:
                    output.append("")
                    output.append("⚠️ Warning: Replication lag > 10 seconds")
                elif lag_seconds > 60:
                    output.append("")
                    output.append("🔴 Critical: Replication lag > 1 minute")
                else:
                    output.append("")
                    output.append("✓ Replication lag is acceptable")

        else:
            output.append("Role: Primary (Master)")
            output.append("")

            # Check for connected replicas
            cursor.execute(
                """
                SELECT 
                    client_addr,
                    state,
                    sync_state,
                    EXTRACT(EPOCH FROM (now() - backend_start)) AS connection_age_seconds,
                    EXTRACT(EPOCH FROM (now() - state_change)) AS state_age_seconds,
                    replay_lag,
                    write_lag,
                    flush_lag
                FROM pg_stat_replication;
            """
            )

            replicas = cursor.fetchall()

            if replicas:
                output.append(f"Connected Replicas: {len(replicas)}")
                output.append("")

                for idx, replica in enumerate(replicas, 1):
                    (
                        client_addr,
                        state,
                        sync_state,
                        conn_age,
                        state_age,
                        replay_lag,
                        write_lag,
                        flush_lag,
                    ) = replica

                    output.append(f"Replica {idx}:")
                    output.append(f"  Address: {client_addr}")
                    output.append(f"  State: {state}")
                    output.append(f"  Sync State: {sync_state}")
                    output.append(f"  Connected: {conn_age:.0f}s ago")

                    if replay_lag:
                        lag_ms = replay_lag.total_seconds() * 1000
                        output.append(f"  Replay Lag: {lag_ms:.2f}ms")

                    output.append("")

                output.append("✓ Replication is active")
            else:
                output.append("No replicas connected")
                output.append("💡 This is normal for standalone instances")

        cursor.close()
        conn.close()

        return "\n".join(output)

    except psycopg.Error as e:
        return f"✗ PostgreSQL connection error: {e}"
    except Exception as e:
        return f"✗ Error checking replication status: {str(e)}"


@tool("Check Table Bloat")
def check_table_bloat(min_bloat_mb: int = 100) -> str:
    """
    Identify bloated tables that need VACUUM FULL or rebuilding.

    Args:
        min_bloat_mb: Minimum bloat size in MB to report (default 100MB)

    Returns:
        List of bloated tables with wasted space

    Use Cases:
        - Identify tables needing maintenance
        - Plan VACUUM FULL operations
        - Optimize storage usage
        - Performance optimization
    """
    try:
        conn = _get_postgres_connection()
        cursor = conn.cursor()

        # Query to estimate table bloat
        cursor.execute(
            """
            SELECT
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
                pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes,
                CASE WHEN (pg_stat_user_tables.n_dead_tup::float / NULLIF(pg_stat_user_tables.n_live_tup, 0)) > 0.1
                    THEN 'High'
                    WHEN (pg_stat_user_tables.n_dead_tup::float / NULLIF(pg_stat_user_tables.n_live_tup, 0)) > 0.05
                    THEN 'Medium'
                    ELSE 'Low'
                END AS bloat_level,
                pg_stat_user_tables.n_live_tup,
                pg_stat_user_tables.n_dead_tup,
                pg_stat_user_tables.last_vacuum,
                pg_stat_user_tables.last_autovacuum
            FROM pg_tables
            JOIN pg_stat_user_tables ON pg_tables.tablename = pg_stat_user_tables.relname
                AND pg_tables.schemaname = pg_stat_user_tables.schemaname
            WHERE pg_tables.schemaname NOT IN ('pg_catalog', 'information_schema')
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            LIMIT 20;
        """
        )

        tables = cursor.fetchall()

        if not tables:
            cursor.close()
            conn.close()
            return "No user tables found"

        output = [
            "=== Table Bloat Analysis ===",
            f"Analyzing top 20 largest tables",
            f"Bloat threshold: {min_bloat_mb}MB",
            "",
        ]

        bloated_tables = []
        healthy_tables = 0

        for table in tables:
            (
                schema,
                tablename,
                total_size,
                size_bytes,
                bloat_level,
                live_tup,
                dead_tup,
                last_vacuum,
                last_autovacuum,
            ) = table

            # Convert size threshold to bytes
            min_size_bytes = min_bloat_mb * 1024 * 1024

            if bloat_level in ["High", "Medium"] and size_bytes > min_size_bytes:
                bloated_tables.append(
                    {
                        "schema": schema,
                        "table": tablename,
                        "size": total_size,
                        "bloat": bloat_level,
                        "live": live_tup,
                        "dead": dead_tup,
                        "last_vacuum": last_vacuum,
                        "last_autovacuum": last_autovacuum,
                    }
                )
            else:
                healthy_tables += 1

        if bloated_tables:
            output.append(f"⚠️ Found {len(bloated_tables)} bloated tables:")
            output.append("")

            for table in bloated_tables:
                output.append(f"• {table['schema']}.{table['table']}")
                output.append(f"  Size: {table['size']}")
                output.append(f"  Bloat Level: {table['bloat']}")
                output.append(f"  Live Tuples: {table['live']:,}")
                output.append(f"  Dead Tuples: {table['dead']:,}")

                if table["last_vacuum"]:
                    output.append(f"  Last Manual VACUUM: {table['last_vacuum']}")
                if table["last_autovacuum"]:
                    output.append(f"  Last Auto VACUUM: {table['last_autovacuum']}")

                output.append(
                    f"  💡 Consider: VACUUM FULL {table['schema']}.{table['table']};"
                )
                output.append("")
        else:
            output.append(
                f"✓ No significant bloat detected (threshold: {min_bloat_mb}MB)"
            )

        if healthy_tables > 0:
            output.append(f"{healthy_tables} tables are healthy")

        cursor.close()
        conn.close()

        return "\n".join(output)

    except psycopg.Error as e:
        return f"✗ PostgreSQL connection error: {e}"
    except Exception as e:
        return f"✗ Error checking table bloat: {str(e)}"


@tool("Analyze Slow Queries")
def analyze_slow_queries(min_duration_ms: int = 1000, limit: int = 10) -> str:
    """
    Analyze slowest queries with execution statistics.

    Args:
        min_duration_ms: Minimum duration in milliseconds (default 1000ms = 1s)
        limit: Number of queries to return (default 10)

    Returns:
        Top slow queries with execution stats and optimization hints

    Use Cases:
        - Identify performance bottlenecks
        - Query optimization
        - Index planning
        - Performance troubleshooting

    Note: Requires pg_stat_statements extension
    """
    try:
        conn = _get_postgres_connection()
        cursor = conn.cursor()

        # Check if pg_stat_statements is available
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
            );
        """
        )

        extension_exists = cursor.fetchone()[0]

        if not extension_exists:
            cursor.close()
            conn.close()
            return """
✗ pg_stat_statements extension not installed

To enable query statistics tracking:
1. Add to postgresql.conf: shared_preload_libraries = 'pg_stat_statements'
2. Restart PostgreSQL
3. Run: CREATE EXTENSION pg_stat_statements;

This extension is required for detailed query performance analysis.
"""

        # Get slow queries
        cursor.execute(
            f"""
            SELECT
                query,
                calls,
                ROUND(total_exec_time::numeric, 2) AS total_time_ms,
                ROUND(mean_exec_time::numeric, 2) AS mean_time_ms,
                ROUND(max_exec_time::numeric, 2) AS max_time_ms,
                ROUND(stddev_exec_time::numeric, 2) AS stddev_time_ms,
                rows
            FROM pg_stat_statements
            WHERE mean_exec_time > {min_duration_ms}
                AND query NOT LIKE '%pg_stat_statements%'
            ORDER BY mean_exec_time DESC
            LIMIT {limit};
        """
        )

        slow_queries = cursor.fetchall()

        if not slow_queries:
            cursor.close()
            conn.close()
            return f"""
=== Slow Query Analysis ===

✓ No queries found with mean execution time > {min_duration_ms}ms

Your database queries are performing well!
"""

        output = [
            "=== Slow Query Analysis ===",
            f"Threshold: {min_duration_ms}ms",
            f"Top {len(slow_queries)} slowest queries:",
            "",
        ]

        for idx, query_stat in enumerate(slow_queries, 1):
            query, calls, total_time, mean_time, max_time, stddev_time, rows = (
                query_stat
            )

            # Truncate long queries
            display_query = query[:200] + "..." if len(query) > 200 else query

            output.append(f"Query #{idx}:")
            output.append(f"  SQL: {display_query}")
            output.append(f"  Calls: {calls:,}")
            output.append(f"  Mean Time: {mean_time:.2f}ms")
            output.append(f"  Max Time: {max_time:.2f}ms")
            output.append(f"  Total Time: {total_time:.2f}ms")
            output.append(f"  Rows Returned: {rows:,}")

            # Add optimization hints
            if mean_time > 5000:
                output.append(
                    "  ⚠️ CRITICAL: Consider major optimization or query rewrite"
                )
            elif mean_time > 2000:
                output.append("  ⚠️ HIGH: Review indexes and query plan")
            else:
                output.append("  💡 Consider adding indexes or optimizing")

            output.append("")

        output.append(
            "💡 Use EXPLAIN ANALYZE on these queries for detailed execution plans"
        )

        cursor.close()
        conn.close()

        return "\n".join(output)

    except psycopg.Error as e:
        return f"✗ PostgreSQL connection error: {e}"
    except Exception as e:
        return f"✗ Error analyzing slow queries: {str(e)}"


@tool("Check Index Health")
def check_index_health() -> str:
    """
    Analyze index usage and identify unused or missing indexes.

    Returns:
        Index usage statistics, unused indexes, and suggestions

    Use Cases:
        - Identify unused indexes (wasting space and write performance)
        - Detect missing indexes on frequently scanned tables
        - Index bloat detection
        - Performance optimization
    """
    try:
        conn = _get_postgres_connection()
        cursor = conn.cursor()

        output = ["=== Index Health Analysis ===", ""]

        # Get unused indexes
        cursor.execute(
            """
            SELECT
                schemaname,
                tablename,
                indexname,
                pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
                idx_scan,
                idx_tup_read,
                idx_tup_fetch
            FROM pg_stat_user_indexes
            WHERE idx_scan = 0
                AND schemaname NOT IN ('pg_catalog', 'information_schema')
                AND indexrelname NOT LIKE '%_pkey'
            ORDER BY pg_relation_size(indexrelid) DESC
            LIMIT 10;
        """
        )

        unused_indexes = cursor.fetchall()

        if unused_indexes:
            output.append(f"⚠️ Unused Indexes ({len(unused_indexes)} found):")
            output.append("")

            total_wasted_size = 0
            for idx in unused_indexes:
                schema, table, index_name, size, scans, reads, fetches = idx

                output.append(f"• {schema}.{index_name}")
                output.append(f"  Table: {table}")
                output.append(f"  Size: {size}")
                output.append(f"  Scans: {scans}")
                output.append(f"  💡 Consider: DROP INDEX {schema}.{index_name};")
                output.append("")

            output.append("Note: Verify indexes are truly unused before dropping")
            output.append("")
        else:
            output.append("✓ No unused indexes found")
            output.append("")

        # Get most used indexes
        cursor.execute(
            """
            SELECT
                schemaname,
                tablename,
                indexname,
                idx_scan,
                pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
            FROM pg_stat_user_indexes
            WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
            ORDER BY idx_scan DESC
            LIMIT 10;
        """
        )

        used_indexes = cursor.fetchall()

        if used_indexes:
            output.append(f"Top 10 Most Used Indexes:")
            output.append("")

            for idx in used_indexes:
                schema, table, index_name, scans, size = idx

                output.append(f"• {schema}.{index_name} ({table})")
                output.append(f"  Scans: {scans:,}")
                output.append(f"  Size: {size}")
                output.append("")

        # Check for tables with sequential scans but no index scans
        cursor.execute(
            """
            SELECT
                schemaname,
                tablename,
                seq_scan,
                seq_tup_read,
                idx_scan,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS table_size
            FROM pg_stat_user_tables
            WHERE seq_scan > 100
                AND idx_scan < seq_scan / 10
                AND schemaname NOT IN ('pg_catalog', 'information_schema')
            ORDER BY seq_scan DESC
            LIMIT 5;
        """
        )

        seq_scan_tables = cursor.fetchall()

        if seq_scan_tables:
            output.append("⚠️ Tables with High Sequential Scans (may need indexes):")
            output.append("")

            for table in seq_scan_tables:
                schema, tablename, seq_scans, seq_reads, idx_scans, size = table

                output.append(f"• {schema}.{tablename}")
                output.append(f"  Size: {size}")
                output.append(f"  Sequential Scans: {seq_scans:,}")
                output.append(f"  Index Scans: {idx_scans:,}")
                output.append(f"  💡 Consider adding indexes for common WHERE clauses")
                output.append("")

        cursor.close()
        conn.close()

        return "\n".join(output)

    except psycopg.Error as e:
        return f"✗ PostgreSQL connection error: {e}"
    except Exception as e:
        return f"✗ Error checking index health: {str(e)}"


@tool("Monitor Vacuum Status")
def monitor_vacuum_status() -> str:
    """
    Monitor VACUUM and ANALYZE operations status.

    Returns:
        Vacuum statistics, autovacuum status, and table maintenance info

    Use Cases:
        - Verify autovacuum is running
        - Track vacuum progress
        - Identify tables needing maintenance
        - Performance optimization
    """
    try:
        conn = _get_postgres_connection()
        cursor = conn.cursor()

        output = ["=== VACUUM Status ===", ""]

        # Check autovacuum configuration
        cursor.execute(
            """
            SELECT name, setting, unit
            FROM pg_settings
            WHERE name IN ('autovacuum', 'autovacuum_max_workers', 'autovacuum_naptime');
        """
        )

        autovacuum_config = cursor.fetchall()

        output.append("Autovacuum Configuration:")
        for config in autovacuum_config:
            name, setting, unit = config
            unit_str = f" {unit}" if unit else ""
            output.append(f"  {name}: {setting}{unit_str}")
        output.append("")

        # Check current vacuum operations
        cursor.execute(
            """
            SELECT
                datname,
                usename,
                state,
                query,
                EXTRACT(EPOCH FROM (now() - query_start)) AS duration_seconds
            FROM pg_stat_activity
            WHERE query LIKE '%VACUUM%' OR query LIKE '%ANALYZE%'
                AND query NOT LIKE '%pg_stat_activity%'
                AND state != 'idle';
        """
        )

        active_vacuums = cursor.fetchall()

        if active_vacuums:
            output.append(f"Active VACUUM Operations: {len(active_vacuums)}")
            output.append("")

            for vac in active_vacuums:
                db, user, state, query, duration = vac
                query_display = query[:100] + "..." if len(query) > 100 else query

                output.append(f"• Database: {db}")
                output.append(f"  User: {user}")
                output.append(f"  Query: {query_display}")
                output.append(f"  Duration: {duration:.0f}s")
                output.append("")
        else:
            output.append("No active VACUUM operations")
            output.append("")

        # Get tables that need vacuuming
        cursor.execute(
            """
            SELECT
                schemaname,
                tablename,
                n_dead_tup,
                n_live_tup,
                ROUND(100.0 * n_dead_tup / NULLIF(n_live_tup, 0), 2) AS dead_tup_pct,
                last_vacuum,
                last_autovacuum,
                last_analyze,
                last_autoanalyze
            FROM pg_stat_user_tables
            WHERE n_dead_tup > 1000
            ORDER BY n_dead_tup DESC
            LIMIT 10;
        """
        )

        needs_vacuum = cursor.fetchall()

        if needs_vacuum:
            output.append("Tables with Dead Tuples (may need VACUUM):")
            output.append("")

            for table in needs_vacuum:
                (
                    schema,
                    tablename,
                    dead,
                    live,
                    pct,
                    last_vac,
                    last_autovac,
                    last_analyze,
                    last_autoanalyze,
                ) = table

                output.append(f"• {schema}.{tablename}")
                output.append(f"  Dead Tuples: {dead:,} ({pct:.1f}% of live tuples)")
                output.append(f"  Live Tuples: {live:,}")

                if last_vac:
                    output.append(f"  Last Manual VACUUM: {last_vac}")
                if last_autovac:
                    output.append(f"  Last Auto VACUUM: {last_autovac}")

                if pct > 20:
                    output.append(
                        f"  ⚠️ Consider manual VACUUM: VACUUM ANALYZE {schema}.{tablename};"
                    )

                output.append("")
        else:
            output.append(
                "✓ All tables are well-maintained (no significant dead tuples)"
            )

        cursor.close()
        conn.close()

        return "\n".join(output)

    except psycopg.Error as e:
        return f"✗ PostgreSQL connection error: {e}"
    except Exception as e:
        return f"✗ Error monitoring vacuum status: {str(e)}"


@tool("Check Database Locks")
def check_database_locks() -> str:
    """
    Analyze current database locks and blocking queries.

    Returns:
        Active locks, blocking relationships, and long-running transactions

    Use Cases:
        - Troubleshoot slow queries
        - Identify deadlocks
        - Detect blocking sessions
        - Performance troubleshooting
    """
    try:
        conn = _get_postgres_connection()
        cursor = conn.cursor()

        output = ["=== Database Locks Analysis ===", ""]

        # Get blocking locks
        cursor.execute(
            """
            SELECT
                blocked_locks.pid AS blocked_pid,
                blocked_activity.usename AS blocked_user,
                blocking_locks.pid AS blocking_pid,
                blocking_activity.usename AS blocking_user,
                blocked_activity.query AS blocked_statement,
                blocking_activity.query AS blocking_statement,
                blocked_locks.locktype,
                blocked_locks.mode AS blocked_mode,
                blocking_locks.mode AS blocking_mode
            FROM pg_catalog.pg_locks blocked_locks
            JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
            JOIN pg_catalog.pg_locks blocking_locks
                ON blocking_locks.locktype = blocked_locks.locktype
                AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
                AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
                AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
                AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
                AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
                AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
                AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
                AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
                AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
                AND blocking_locks.pid != blocked_locks.pid
            JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
            WHERE NOT blocked_locks.granted;
        """
        )

        blocking_locks = cursor.fetchall()

        if blocking_locks:
            output.append(
                f"🔴 BLOCKING DETECTED: {len(blocking_locks)} blocked queries"
            )
            output.append("")

            for idx, lock in enumerate(blocking_locks, 1):
                (
                    blocked_pid,
                    blocked_user,
                    blocking_pid,
                    blocking_user,
                    blocked_query,
                    blocking_query,
                    locktype,
                    blocked_mode,
                    blocking_mode,
                ) = lock

                blocked_display = (
                    blocked_query[:150] + "..."
                    if len(blocked_query) > 150
                    else blocked_query
                )
                blocking_display = (
                    blocking_query[:150] + "..."
                    if len(blocking_query) > 150
                    else blocking_query
                )

                output.append(f"Lock #{idx}:")
                output.append(f"  Blocked PID: {blocked_pid} (user: {blocked_user})")
                output.append(f"  Blocked Query: {blocked_display}")
                output.append(f"  Lock Type: {locktype}, Mode: {blocked_mode}")
                output.append("")
                output.append(f"  Blocking PID: {blocking_pid} (user: {blocking_user})")
                output.append(f"  Blocking Query: {blocking_display}")
                output.append(f"  Blocking Mode: {blocking_mode}")
                output.append("")
                output.append(
                    f"  💡 To terminate blocking query: SELECT pg_terminate_backend({blocking_pid});"
                )
                output.append("")
        else:
            output.append("✓ No blocking locks detected")
            output.append("")

        # Get lock summary
        cursor.execute(
            """
            SELECT
                locktype,
                mode,
                COUNT(*) as lock_count
            FROM pg_locks
            WHERE granted = true
            GROUP BY locktype, mode
            ORDER BY lock_count DESC
            LIMIT 10;
        """
        )

        lock_summary = cursor.fetchall()

        if lock_summary:
            output.append("Current Lock Summary (top 10):")
            for lock in lock_summary:
                locktype, mode, count = lock
                output.append(f"  {locktype} ({mode}): {count} locks")
            output.append("")

        # Get long-running transactions
        cursor.execute(
            """
            SELECT
                pid,
                usename,
                state,
                EXTRACT(EPOCH FROM (now() - xact_start)) AS xact_duration_seconds,
                query
            FROM pg_stat_activity
            WHERE state != 'idle'
                AND xact_start IS NOT NULL
                AND EXTRACT(EPOCH FROM (now() - xact_start)) > 60
            ORDER BY xact_start
            LIMIT 5;
        """
        )

        long_txns = cursor.fetchall()

        if long_txns:
            output.append(f"⚠️ Long-Running Transactions (> 60s): {len(long_txns)}")
            output.append("")

            for txn in long_txns:
                pid, user, state, duration, query = txn
                query_display = query[:150] + "..." if len(query) > 150 else query

                output.append(f"• PID: {pid} (user: {user})")
                output.append(f"  Duration: {duration:.0f}s")
                output.append(f"  State: {state}")
                output.append(f"  Query: {query_display}")
                output.append("")

        cursor.close()
        conn.close()

        return "\n".join(output)

    except psycopg.Error as e:
        return f"✗ PostgreSQL connection error: {e}"
    except Exception as e:
        return f"✗ Error checking database locks: {str(e)}"


@tool("Vacuum PostgreSQL Table")
def vacuum_postgres_table(
    database: str, table: str, full: bool = False, dry_run: bool = False
) -> str:
    """
    Run VACUUM on a PostgreSQL table to reclaim space and update statistics.

    Args:
        database: Database name
        table: Table name
        full: If True, run VACUUM FULL (requires exclusive lock, reclaims more space)
        dry_run: If True, only show what would be done

    Returns:
        Status message with vacuum results

    Safety:
        - VACUUM FULL requires approval (exclusive table lock)
        - Regular VACUUM is non-blocking
        - Checks table exists before running

    Use cases:
        - Reclaim space from dead tuples (detected by check_table_bloat)
        - Update table statistics for query planner
        - Improve query performance
    """
    try:
        import psycopg

        # PostgreSQL connection params
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = int(os.getenv("POSTGRES_PORT", "5432"))
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "")

        vacuum_type = "VACUUM FULL" if full else "VACUUM"

        if dry_run:
            return f"🔍 DRY-RUN: Would run {vacuum_type} on table '{table}' in database '{database}'\n\n⚠️ {'Exclusive lock required - blocks all access' if full else 'Non-blocking operation'}"

        # Check if critical database or VACUUM FULL and request approval
        approval_manager = get_approval_manager()
        if approval_manager.is_critical_service("databases", database) or full:
            details = (
                f"Database: {database}\nTable: {table}\nOperation: {vacuum_type}\n"
            )
            details += (
                "⚠️ Exclusive lock required - blocks table access"
                if full
                else "Non-blocking operation"
            )

            approval_result = approval_manager.send_approval_request(
                action=f"{vacuum_type} on {database}.{table}",
                details=details,
                severity="critical" if full else "warning",
            )

            if not approval_result["approved"]:
                return f"❌ Action rejected: {approval_result['reason']}\nVACUUM NOT executed on {database}.{table}"

        # Connect to database
        conn = psycopg.connect(
            host=host,
            port=port,
            dbname=database,
            user=user,
            password=password,
            autocommit=True,  # VACUUM requires autocommit
        )

        cursor = conn.cursor()

        # Check if table exists
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = %s
            )
        """,
            (table,),
        )

        if not cursor.fetchone()[0]:
            conn.close()
            return f"❌ Table '{table}' does not exist in database '{database}'"

        # Get table size before vacuum
        cursor.execute(f"SELECT pg_total_relation_size('{table}')")
        size_before = cursor.fetchone()[0]

        # Run VACUUM
        import time

        start_time = time.time()

        if full:
            cursor.execute(f"VACUUM FULL {table}")
        else:
            cursor.execute(f"VACUUM ANALYZE {table}")

        duration = time.time() - start_time

        # Get table size after vacuum
        cursor.execute(f"SELECT pg_total_relation_size('{table}')")
        size_after = cursor.fetchone()[0]

        conn.close()

        space_reclaimed = size_before - size_after

        output = [f"✅ Successfully completed {vacuum_type} on table '{table}'\n"]
        output.append(f"**Database**: {database}")
        output.append(f"**Table**: {table}")
        output.append(f"**Duration**: {duration:.2f} seconds")
        output.append(f"**Size Before**: {size_before / (1024**2):.2f} MB")
        output.append(f"**Size After**: {size_after / (1024**2):.2f} MB")
        output.append(f"**Space Reclaimed**: {space_reclaimed / (1024**2):.2f} MB")

        return "\n".join(output)

    except Exception as e:
        return f"❌ Error running vacuum: {str(e)}"


@tool("Clear PostgreSQL Connections")
def clear_postgres_connections(
    database: str, force_user: str = None, dry_run: bool = False
) -> str:
    """
    Terminate active connections to a PostgreSQL database.

    Args:
        database: Database name
        force_user: If specified, only kill connections from this user
        dry_run: If True, only show what would be killed

    Returns:
        Status message with number of connections terminated

    Safety:
        - Requires approval (terminates active sessions)
        - Logs all terminated sessions
        - Does not kill superuser connections

    Use cases:
        - Database locked by long-running query
        - Need exclusive access for maintenance
        - Clear idle connections
    """
    try:
        import psycopg

        host = os.getenv("POSTGRES_HOST", "localhost")
        port = int(os.getenv("POSTGRES_PORT", "5432"))
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "")

        # Connect to postgres database (not the target database)
        conn = psycopg.connect(
            host=host,
            port=port,
            dbname="postgres",
            user=user,
            password=password,
            autocommit=True,
        )

        cursor = conn.cursor()

        # Get list of active connections
        query = """
            SELECT pid, usename, application_name, state,
                   query_start, state_change
            FROM pg_stat_activity
            WHERE datname = %s
              AND pid != pg_backend_pid()
        """

        params = [database]

        if force_user:
            query += " AND usename = %s"
            params.append(force_user)

        cursor.execute(query, params)
        connections = cursor.fetchall()

        if not connections:
            conn.close()
            return f"ℹ️ No active connections found to database '{database}'"

        if dry_run:
            output = [
                f"🔍 DRY-RUN: Would terminate {len(connections)} connection(s) to '{database}'\n"
            ]
            output.append("**Connections to be terminated**:")
            for conn_info in connections:
                pid, username, app, state, query_start, state_change = conn_info
                output.append(f"  • PID {pid}: {username} ({app}) - {state}")
            conn.close()
            return "\n".join(output)

        # Check if critical database and request approval
        approval_manager = get_approval_manager()
        if approval_manager.is_critical_service("databases", database):
            details = (
                f"Database: {database}\nConnections to terminate: {len(connections)}\n"
            )
            if force_user:
                details += f"User filter: {force_user}\n"
            details += "\nConnections:\n"
            for conn_info in connections:
                pid, username, app, state, _, _ = conn_info
                details += f"  • PID {pid}: {username} ({app}) - {state}\n"

            approval_result = approval_manager.send_approval_request(
                action=f"Terminate {len(connections)} connection(s) to {database}",
                details=details,
                severity="critical",
            )

            if not approval_result["approved"]:
                conn.close()
                return f"❌ Action rejected: {approval_result['reason']}\nConnections NOT terminated"

        # Terminate connections
        terminated = []
        for conn_info in connections:
            pid = conn_info[0]
            try:
                cursor.execute("SELECT pg_terminate_backend(%s)", (pid,))
                terminated.append(pid)
            except Exception as e:
                # Connection may have already closed
                pass

        conn.close()

        output = [
            f"✅ Terminated {len(terminated)} connection(s) to database '{database}'\n"
        ]
        output.append(f"**PIDs Terminated**: {', '.join(map(str, terminated))}")
        if force_user:
            output.append(f"**User Filter**: {force_user}")

        return "\n".join(output)

    except Exception as e:
        return f"❌ Error clearing connections: {str(e)}"
