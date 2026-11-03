"""
tools.py - DBA Tools for the Agent

What this component does:
Contains Python functions that serve as 'Tools' for the AI Agent.
In Agentic AI, the LLM cannot directly touch your database. Instead, you provide
it with a menu of tools. The LLM reads the function names, parameter types,
and docstrings (descriptions) to decide:
  1. Which tool to call based on what the user asked.
  2. What arguments to pass to the tool.

Our agent then runs the function, gets real data from SQL Server,
and returns it back to the LLM.
"""

from db import execute_query
import json


def _log_tool_call(tool_name: str, args: dict = None):
    print(f"\n  >>> [AGENT ACTION: TOOL CALLED] -> `{tool_name}`")
    if args:
        print(f"      Arguments: {json.dumps(args)}")


def _log_tool_result(result):
    if isinstance(result, list):
        count = len(result)
        print(f"  >>> [OBSERVATION FROM SQL SERVER] -> Retrieved {count} row(s)")
    elif isinstance(result, dict):
        print(f"  >>> [OBSERVATION FROM SQL SERVER] -> Status returned successfully")


def get_server_overview() -> dict:
    """
    Retrieves high-level SQL Server instance health, version, uptime, and hardware capacity.
    Use this tool when the user asks:
      - "What server is this?"
      - "What version of SQL Server are we running?"
      - "How long has SQL Server been up?"
      - "Give me a general server health or status overview."
    """
    _log_tool_call("get_server_overview")
    sql = """
    SELECT 
        @@SERVERNAME AS server_name,
        CAST(SERVERPROPERTY('Edition') AS VARCHAR(100)) AS edition,
        CAST(SERVERPROPERTY('ProductVersion') AS VARCHAR(50)) AS product_version,
        sqlserver_start_time,
        cpu_count,
        physical_memory_kb / 1024 AS physical_memory_mb
    FROM sys.dm_os_sys_info
    """
    rows = execute_query(sql)
    if rows and "error" not in rows[0]:
        res = {"server_overview": rows[0]}
        _log_tool_result(res)
        return res
    _log_tool_result(rows)
    return {"error": rows[0].get("error", "Unknown error")}


def list_databases() -> list[dict]:
    """
    Lists all databases on the SQL Server instance along with their state,
    recovery model, compatibility level, and size in megabytes (MB).
    Use this tool when the user asks:
      - "What databases exist on this server?"
      - "Check database status or sizes."
      - "Are any databases offline or recovering?"
    """
    _log_tool_call("list_databases")
    sql = """
    SELECT 
        d.name AS database_name,
        d.state_desc AS state,
        d.recovery_model_desc AS recovery_model,
        d.compatibility_level,
        CAST(SUM(mf.size) * 8.0 / 1024 AS DECIMAL(10,2)) AS size_mb
    FROM sys.databases d
    JOIN sys.master_files mf ON d.database_id = mf.database_id
    GROUP BY d.name, d.state_desc, d.recovery_model_desc, d.compatibility_level
    ORDER BY size_mb DESC
    """
    results = execute_query(sql)
    _log_tool_result(results)
    return results


def get_active_requests_and_waits() -> list[dict]:
    """
    Inspects real-time running sessions and DMV requests on SQL Server.
    Identifies blocking queries, wait types, CPU time, and running T-SQL text.
    Use this tool when the user asks:
      - "Are there any blocked sessions?"
      - "Why is the database slow right now?"
      - "Show currently executing queries and wait stats."
      - "Is any query causing high CPU right now?"
    """
    _log_tool_call("get_active_requests_and_waits")
    sql = """
    SELECT 
        r.session_id,
        r.status,
        r.command,
        r.cpu_time,
        r.total_elapsed_time,
        r.wait_type,
        r.wait_time,
        r.blocking_session_id,
        SUBSTRING(t.text, (r.statement_start_offset/2)+1,
            ((CASE r.statement_end_offset
                WHEN -1 THEN DATALENGTH(t.text)
                ELSE r.statement_end_offset
            END - r.statement_start_offset)/2) + 1) AS statement_text
    FROM sys.dm_exec_requests r
    CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) t
    WHERE r.session_id != @@SPID AND r.session_id > 50
    """
    results = execute_query(sql)
    if not results:
        res = [{"message": "No active user sessions or blocked requests at this moment."}]
        _log_tool_result(res)
        return res
    _log_tool_result(results)
    return results


def get_top_resource_queries(order_by: str = "cpu", top_n: int = 5) -> list[dict]:
    """
    Retrieves historical top resource-consuming queries from the plan cache.
    
    Args:
        order_by: Metric to sort by. Supported values: 'cpu', 'reads', 'elapsed_time'.
                  Defaults to 'cpu'.
        top_n: Number of queries to return (default 5).
        
    Use this tool when the user asks:
      - "What are the most expensive queries on this server?"
      - "Which queries use the most CPU or do the most I/O reads?"
    """
    _log_tool_call("get_top_resource_queries", {"order_by": order_by, "top_n": top_n})
    sort_column = "total_worker_time"
    if order_by.lower() in ("reads", "io"):
        sort_column = "total_logical_reads"
    elif order_by.lower() in ("elapsed", "time", "duration"):
        sort_column = "total_elapsed_time"

    sql = f"""
    SELECT TOP {int(top_n)}
        qs.execution_count,
        qs.total_worker_time / 1000 AS total_cpu_ms,
        qs.total_worker_time / qs.execution_count / 1000 AS avg_cpu_ms,
        qs.total_elapsed_time / 1000 AS total_elapsed_ms,
        qs.total_logical_reads,
        qs.last_execution_time,
        SUBSTRING(st.text, (qs.statement_start_offset/2)+1,
            ((CASE qs.statement_end_offset
                WHEN -1 THEN DATALENGTH(st.text)
                ELSE qs.statement_end_offset
            END - qs.statement_start_offset)/2) + 1) AS query_text
    FROM sys.dm_exec_query_stats qs
    CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
    ORDER BY qs.{sort_column} DESC
    """
    results = execute_query(sql)
    _log_tool_result(results)
    return results


def execute_safe_query(sql_query: str) -> list[dict]:
    """
    Executes a custom ad-hoc read-only T-SQL query against SQL Server.
    SAFETY GUARD: Strictly blocks non-SELECT statements (INSERT, UPDATE, DELETE,
    DROP, ALTER, TRUNCATE, EXEC, SHUTDOWN, etc.).
    
    Args:
        sql_query: Read-only SELECT query string.
        
    Use this tool ONLY when none of the standard tools can answer the user's specific request.
    """
    _log_tool_call("execute_safe_query", {"sql_query": sql_query})
    # Guardrail check
    forbidden = [
        "INSERT ", "UPDATE ", "DELETE ", "DROP ", "ALTER ", 
        "TRUNCATE ", "EXEC ", "EXECUTE ", "GRANT ", "REVOKE ",
        "CREATE ", "SHUTDOWN ", "BACKUP ", "RESTORE "
    ]
    normalized = " " + sql_query.upper().strip()
    for word in forbidden:
        if word in normalized:
            err = [{"error": f"Security Violation: '{word.strip()}' statements are strictly blocked. Safe read-only SELECT queries only."}]
            _log_tool_result(err)
            return err
            
    if not normalized.strip().startswith("SELECT") and not normalized.strip().startswith("WITH"):
        err = [{"error": "Security Violation: Only SELECT or WITH queries are permitted."}]
        _log_tool_result(err)
        return err

    results = execute_query(sql_query)
    _log_tool_result(results)
    return results


# List of all tools available to the Agent
DBA_TOOLS = [
    get_server_overview,
    list_databases,
    get_active_requests_and_waits,
    get_top_resource_queries,
    execute_safe_query
]

# Map of tool names to actual Python callable functions
TOOL_MAP = {func.__name__: func for func in DBA_TOOLS}
