"""
agent.py - The SQL Server DBA Agent Orchestrator

What this component does:
This is the BRAIN and the AGENT LOOP.
It connects the LLM (Gemini) with the Tools (tools.py) and the User.

How an Agent works (The ReAct Loop):
1. USER PROMPT: User asks in plain English (e.g., "Are there any slow queries or blocked sessions?")
2. REASONING: Gemini analyzes the request, realizes it cannot answer from memory,
   and selects the right tool (e.g., `get_active_requests_and_waits`).
3. ACTION: The Agent intercepts the tool request and executes the Python function against SQL Server.
4. OBSERVATION: The Agent feeds the query result (data/error) back to Gemini.
5. SYNTHESIS: Gemini analyzes the raw SQL data and formulates a helpful DBA summary with recommendations.
"""

import sys
import json
from google import genai
from google.genai import types

import config
from tools import DBA_TOOLS, TOOL_MAP

SYSTEM_INSTRUCTION = """
You are an expert Microsoft SQL Server Senior Database Administrator (DBA) AI Agent.
Your mission is to help administrators monitor, troubleshoot, and optimize SQL Server instances.

Operational Principles:
1. When asked about databases, server health, active queries, or resource usage, ALWAYS use your available tools to inspect live data. Do not guess or make up data.
2. If the user asks a general diagnostic question (e.g., "Why is my server slow?"), first check for active blocking or running queries with `get_active_requests_and_waits` and examine server hardware/overview.
3. If no standard tool covers the user's specific request, you may use `execute_safe_query` with a safe read-only SELECT query.
4. Always explain your findings in a clear, professional DBA format:
   - Summary of findings
   - Key metrics (CPU, wait types, sizes, states)
   - Specific, actionable recommendations (e.g. index tuning, isolation level considerations, space management)
5. NEVER attempt or recommend destructive operations without explicit confirmation.
"""


class DBAgent:
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or config.GEMINI_API_KEY
        self.model_name = model or config.GEMINI_MODEL
        self.client = None
        self.chat = None
        
        # Resilient fallback models if the primary model experiences high demand (503) or rate limits (429)
        candidates = [self.model_name, "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.8-flash"]
        self.fallback_models = []
        for m in candidates:
            if m not in self.fallback_models:
                self.fallback_models.append(m)

        if not self.api_key or self.api_key.strip() == "":
            print("\n[WARNING] No GEMINI_API_KEY found in .env or environment.")
            print("[INFO] You can get a free API key at: https://aistudio.google.com/")
        else:
            self._init_gemini_client(self.model_name)

    def _init_gemini_client(self, model: str):
        """Initializes the Google GenAI client and multi-turn chat session with tools."""
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model
        
        # Tools are provided as Python callables.
        # The Google GenAI SDK automatically parses docstrings and type hints.
        self.chat = self.client.chats.create(
            model=self.model_name,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                tools=DBA_TOOLS,
                temperature=0.2, # Low temperature for accurate, factual DBA reasoning
            )
        )

    def ask(self, user_prompt: str) -> str:
        """
        Sends a prompt to the Agent, manages tool calls, and returns the final response.
        Automatically handles transient 503 high-demand or 429 rate limit errors with failover.
        """
        if not self.client:
            return (
                "Error: GEMINI_API_KEY is not configured.\n"
                "Please add your key to the `.env` file (see .env.example) and try again."
            )

        print(f"\n" + "=" * 65)
        print(f"[*] USER INPUT: {user_prompt}")
        print("=" * 65)

        for attempt, model in enumerate(self.fallback_models):
            try:
                print(f"[*] Agent consulting Gemini (Model: `{model}`)...")
                if self.model_name != model or self.chat is None:
                    self._init_gemini_client(model)

                response = self.chat.send_message(user_prompt)
                return response.text
            except Exception as e:
                err_str = str(e)
                # Check for transient capacity / demand errors (503) or rate limits (429) or deprecated (404)
                if any(code in err_str for code in ("503", "429", "404", "UNAVAILABLE", "ResourceExhausted", "high demand")):
                    print(f"\n[NOTICE] Model `{model}` is temporarily busy or unavailable.")
                    if attempt + 1 < len(self.fallback_models):
                        next_model = self.fallback_models[attempt + 1]
                        print(f"         Automatically failing over to fallback model: `{next_model}`...")
                        continue
                return f"Agent execution error: {err_str}"
        return "Agent error: All candidate models were temporarily unavailable. Please retry in a few seconds."


def run_simulated_demo():
    """
    Demonstrates the ReAct loop mechanics step-by-step using real local SQL Server data,
    even before the user pastes their Gemini API key.
    """
    print("\n" + "=" * 70)
    print("DEMONSTRATION: The Agent ReAct Loop (Step-by-Step)")
    print("=" * 70)
    
    print("\nStep 1: User Request")
    print('  User says: "Check which databases are online and show me their sizes."')
    
    print("\nStep 2: LLM Reasoning (Inside Gemini)")
    print('  Gemini reads the prompt and matches it against available Tools in tools.py.')
    print('  Gemini decides: "I should call list_databases() with no arguments."')
    print('  Gemini sends a Tool Call request: {"name": "list_databases", "args": {}}')
    
    print("\nStep 3: Tool Execution (Connecting to local SQL Server)")
    print("  Executing tool: list_databases()...")
    from tools import list_databases
    data = list_databases()
    print(f"  [pyodbc] Query succeeded! Retrieved {len(data)} databases from local SQL Server.")
    print("  Sample records retrieved:")
    for db in data[:3]:
        print(f"    - {db.get('database_name')}: {db.get('state')} ({db.get('size_mb')} MB, {db.get('recovery_model')})")
    
    print("\nStep 4: Observation Ingestion")
    print("  The Agent sends the JSON result back to Gemini as an 'observation'.")
    
    print("\nStep 5: Final Response Synthesis")
    print("  Gemini reads the live data and composes a human-readable DBA summary:")
    total_size = sum(float(x.get('size_mb', 0)) for x in data)
    print(f'  "You currently have {len(data)} databases on this instance totaling {total_size:,.2f} MB.')
    print('   All queried databases are currently ONLINE in their respective recovery models."')
    print("=" * 70)

