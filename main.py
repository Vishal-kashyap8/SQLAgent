"""
main.py - Interactive SQL Server DBA Agent Console

Run this script to interact with your autonomous SQL Server DBA Agent.
Usage:
    python main.py
"""

import sys
import os
import config
from db import test_db_connection
from agent import DBAgent, run_simulated_demo


def print_banner():
    print("=" * 70)
    print("        SQL SERVER DBA - AGENTIC AI ASSISTANT")
    print("      Powered by Google Gemini & Python Tool-Calling")
    print("=" * 70)
    print("Connecting traditional DBA tasks with modern Agentic AI:")
    print("  [LLM Brain]      -> Google Gemini (Reasoning & Decision Making)")
    print("  [Tools/Hands]    -> Python Functions querying DMVs & System Catalogs")
    print("  [Environment]    -> Local SQL Server via pyodbc (Windows Auth)")
    print("=" * 70)


def run_interactive_chat(agent: DBAgent):
    print("\n--- Interactive DBA Agent Mode ---")
    print("Type your question in plain English (or type 'exit' / 'quit' to return).")
    print("Examples:")
    print("  - 'Give me an overview of this SQL Server instance.'")
    print("  - 'Which databases are taking up the most space?'")
    print("  - 'Are there any blocked queries or active wait stats right now?'")
    print("  - 'Show me the top 3 most expensive CPU queries in cache.'")
    print("-" * 70)

    while True:
        try:
            user_input = input("\nDBA Question > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                print("Exiting chat session.")
                break

            response = agent.ask(user_input)
            print("\n" + "-" * 70)
            print("AGENT RESPONSE:")
            print("-" * 70)
            print(response)
            print("-" * 70)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break


def run_preset_scenarios(agent: DBAgent):
    scenarios = [
        ("1. Server Health Check", "What server instance is this, what version are we running, and what is the uptime?"),
        ("2. Database Inventory & Capacity", "List all databases on this instance, show their state, recovery model, and size."),
        ("3. Concurrency & Blocking Diagnostics", "Are there any blocked sessions or queries waiting on resources right now?"),
        ("4. Top CPU Plan Cache Analysis", "Identify the top 3 most CPU-intensive queries in the plan cache and explain what they are doing.")
    ]

    print("\n--- Pre-Crafted DBA Scenarios ---")
    for i, (title, prompt) in enumerate(scenarios, 1):
        print(f"[{i}] {title}")
        print(f"    Prompt: \"{prompt}\"")
    print("[0] Back to Main Menu")

    choice = input("\nSelect a scenario (0-4): ").strip()
    if choice in ("1", "2", "3", "4"):
        idx = int(choice) - 1
        title, prompt = scenarios[idx]
        print(f"\n[RUNNING SCENARIO] {title}")
        response = agent.ask(prompt)
        print("\n" + "-" * 70)
        print("AGENT RESPONSE:")
        print("-" * 70)
        print(response)
        print("-" * 70)


def main():
    print_banner()

    # Pre-flight check for database
    db_status = test_db_connection()
    if db_status.get("status") == "connected":
        print(f"\n[STATUS] Connected to SQL Server: `{db_status.get('server_name')}`")
        print(f"         Version: {db_status.get('version')}")
    else:
        print(f"\n[WARNING] Could not connect to SQL Server: {db_status.get('error')}")
        print("          Check config.py or .env file.")

    has_api_key = bool(config.GEMINI_API_KEY and config.GEMINI_API_KEY.strip())
    if has_api_key:
        print(f"[STATUS] Gemini API Key loaded. Model: `{config.GEMINI_MODEL}`")
    else:
        print(f"[STATUS] No Gemini API Key in .env yet. (Free key: https://aistudio.google.com/)")

    agent = DBAgent() if has_api_key else None

    while True:
        print("\nMain Menu:")
        if has_api_key:
            print("  1. Interactive Chat with DBA Agent")
            print("  2. Run Preset Diagnostic Scenarios")
        print("  3. Run Educational ReAct Loop Simulation (Visual Walkthrough)")
        print("  4. Run Pre-flight Diagnostic Check (test_connection.py)")
        print("  5. Exit")

        choice = input("\nSelect an option (1-5): ").strip()

        if choice == "1":
            if not has_api_key:
                print("\n[!] Please add your GEMINI_API_KEY to the .env file first.")
                print("    Open the `.env` file in this folder and paste your key.")
            else:
                run_interactive_chat(agent)
        elif choice == "2":
            if not has_api_key:
                print("\n[!] Please add your GEMINI_API_KEY to the .env file first.")
            else:
                run_preset_scenarios(agent)
        elif choice == "3":
            run_simulated_demo()
        elif choice == "4":
            import subprocess
            subprocess.run([sys.executable, "test_connection.py"])
        elif choice in ("5", "exit", "quit", "q"):
            print("Goodbye!")
            break
        else:
            print("Invalid option. Please enter 1-5.")


if __name__ == "__main__":
    main()

