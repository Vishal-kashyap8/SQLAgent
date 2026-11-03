"""
test_connection.py - Diagnostic & Verification Script

What this component does:
Tests all prerequisites before you run the agent:
  1. Python packages
  2. Local SQL Server connection (ODBC + Windows Auth)
  3. Gemini API Key & connection (Google AI Studio)
"""

import sys
import config
from db import test_db_connection


def check_sql_server():
    print("\n--- 1. Testing Local SQL Server Connection ---")
    print(f"Target Server: {config.SQL_SERVER}")
    print(f"ODBC Driver  : {config.SQL_DRIVER}")
    print(f"Auth Mode    : {'Windows Authentication' if config.SQL_TRUSTED_CONNECTION else 'SQL Authentication'}")
    
    result = test_db_connection()
    if result.get("status") == "connected":
        print("[SUCCESS] Connected to SQL Server successfully!")
        print(f"  Instance Name: {result.get('server_name')}")
        print(f"  Version      : {result.get('version')}")
        return True
    else:
        print("[FAILED] Could not connect to SQL Server.")
        print(f"  Error details: {result.get('error')}")
        print("\n  Troubleshooting Tip:")
        print("  - If your instance is named (e.g. SQLEXPRESS), set SQL_SERVER=localhost\\SQLEXPRESS in .env")
        print("  - Make sure 'SQL Server' Windows Service is running.")
        return False


def check_gemini_api():
    print("\n--- 2. Testing Gemini API Key ---")
    if not config.GEMINI_API_KEY or config.GEMINI_API_KEY.strip() == "":
        print("[WARNING] GEMINI_API_KEY is not set.")
        print("  You can get a free API key at: https://aistudio.google.com/")
        print("  Then add it to your `.env` file like this:")
        print("  GEMINI_API_KEY=your_actual_api_key_here")
        return False

    print("GEMINI_API_KEY found. Testing API call to Google...")
    try:
        from google import genai
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents="Respond with only: 'Gemini API is ready!'"
        )
        print(f"[SUCCESS] Gemini API responded: {response.text.strip()}")
        return True
    except Exception as e:
        print(f"[FAILED] Gemini API call failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print(" SQL Server DBA Agent - Pre-Flight Diagnostic Check")
    print("=" * 60)
    sql_ok = check_sql_server()
    gemini_ok = check_gemini_api()
    print("\n" + "=" * 60)
    if sql_ok and gemini_ok:
        print(" ALL CHECKS PASSED! You are ready to run: python main.py")
    elif sql_ok and not gemini_ok:
        print(" SQL Server is connected! You can run simulated demo or add your Gemini API key.")
    else:
        print(" Please review the messages above to complete setup.")
    print("=" * 60)

