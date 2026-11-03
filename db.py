"""
db.py - SQL Server Database Connector

What this component does:
Acts as the 'hands' that talk directly to SQL Server using pyodbc.
It manages connections, executes queries, formats result sets into clean Python
dictionaries, and ensures data types (like datetime or Decimal) are JSON-safe.
"""

import pyodbc
from datetime import datetime, date
from decimal import Decimal
import config


def get_connection_string() -> str:
    """Builds the pyodbc connection string based on config.py settings."""
    if config.SQL_TRUSTED_CONNECTION:
        return (
            f"Driver={{{config.SQL_DRIVER}}};"
            f"Server={config.SQL_SERVER};"
            f"Database={config.SQL_DATABASE};"
            "Trusted_Connection=yes;"
            "TrustServerCertificate=yes;"
        )
    else:
        return (
            f"Driver={{{config.SQL_DRIVER}}};"
            f"Server={config.SQL_SERVER};"
            f"Database={config.SQL_DATABASE};"
            f"UID={config.SQL_USERNAME};"
            f"PWD={config.SQL_PASSWORD};"
            "TrustServerCertificate=yes;"
        )


def _serialize_value(val):
    """Converts SQL data types into JSON-serializable Python primitives."""
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, Decimal):
        return float(val)
    return val


def execute_query(query: str, params: tuple = None) -> list[dict]:
    """
    Executes a T-SQL query and returns the results as a list of dictionaries.
    
    Args:
        query: T-SQL query string.
        params: Optional query parameters for parameterized queries.
        
    Returns:
        List of dictionaries where keys are column names.
    """
    conn_str = get_connection_string()
    try:
        with pyodbc.connect(conn_str, timeout=5) as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            if cursor.description is None:
                return [{"message": f"Query executed successfully. Rows affected: {cursor.rowcount}"}]

            columns = [column[0] for column in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append({
                    col: _serialize_value(val)
                    for col, val in zip(columns, row)
                })
            return results
    except Exception as e:
        return [{"error": f"Database execution error: {str(e)}"}]


def test_db_connection() -> dict:
    """Tests the database connection and returns server details."""
    try:
        res = execute_query("SELECT @@SERVERNAME AS server_name, @@VERSION AS version")
        if res and "error" not in res[0]:
            return {
                "status": "connected",
                "server_name": res[0].get("server_name"),
                "version": res[0].get("version", "").split("\n")[0]
            }
        return {"status": "failed", "error": res[0].get("error")}
    except Exception as e:
        return {"status": "failed", "error": str(e)}

