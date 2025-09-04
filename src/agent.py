"""
NL2SQL Agent Module

Tool-based agent implementation using Azure OpenAI function calling.
Based on the nl2sql_agent notebook with modular design.
"""

import json
import os
import sqlite3
import time
from typing import Dict, List, Any, Optional
from pathlib import Path

# Lazy imports - only import when needed
def _get_openai_client():
    from openai import AzureOpenAI
    from dotenv import load_dotenv
    load_dotenv()
    return AzureOpenAI

def _load_env():
    from dotenv import load_dotenv
    load_dotenv()


class AgentTools:
    """Tool functions for the NL2SQL agent"""
    
    @staticmethod
    def discover_database_schema(database_path: str) -> str:
        """Tool: Discover database schema (tables and columns)"""
        try:
            conn = sqlite3.connect(database_path)
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = cursor.fetchall()
            
            schema_info = {}
            
            for (table_name,) in tables:
                # Get columns for each table
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                
                schema_info[table_name] = [
                    {"name": col[1], "type": col[2], "nullable": not col[3]}
                    for col in columns
                ]
            
            conn.close()
            return json.dumps(schema_info, indent=2)
            
        except Exception as e:
            return f"Error discovering schema: {str(e)}"
    
    @staticmethod
    def generate_sql_query(question: str, schema_info: str) -> str:
        """Tool: Generate SQL query from natural language question"""
        try:
            _load_env()
            AzureOpenAI = _get_openai_client()
            client = AzureOpenAI(
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION")
            )
            
            prompt = f"""
You are a SQL expert. Generate a SQLite query for this question.

Database Schema:
{schema_info}

Question: {question}

CRITICAL REQUIREMENTS:
1. NEVER use COUNT(*), SUM(), AVG(), or other aggregation functions
2. ALWAYS return SELECT * FROM table WHERE conditions to show actual rows
3. For "how many" questions, return the matching rows so we can count them by seeing the data
4. For "average" questions, return individual rows so we can see the underlying data
5. The user wants to see the full list of relevant rows corresponding to every answer
6. NEVER EVER use aggregation functions - always return raw matching rows
7. Example: For "how many survived", use SELECT * FROM table WHERE Survived = 1 (NOT SELECT COUNT(*))

Return only the SQL query - no explanations or formatting.
"""
            
            response = client.chat.completions.create(
                model=os.getenv("AZURE_OPENAI_MODEL"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=300
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"Error generating SQL: {str(e)}"
    
    @staticmethod
    def verify_sql_query(sql_query: str, schema_info: str, question: str) -> str:
        """Tool: Verify SQL query for correctness and safety"""
        try:
            # Basic safety checks
            sql_upper = sql_query.strip().upper()
            
            # Check for dangerous operations
            dangerous_ops = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE', 'TRUNCATE']
            for op in dangerous_ops:
                if op in sql_upper:
                    return f"Error: Dangerous operation detected: {op}. Only SELECT queries are allowed."
            
            # Must start with SELECT
            if not sql_upper.startswith('SELECT'):
                return "Error: Only SELECT queries are allowed."
            
            # Check for basic SQL syntax issues
            if sql_query.count('(') != sql_query.count(')'):
                return "Error: Mismatched parentheses in SQL query."
            
            # Use Azure OpenAI to verify the query makes sense
            _load_env()
            AzureOpenAI = _get_openai_client()
            client = AzureOpenAI(
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION")
            )
            
            prompt = f"""
Verify this SQL query for correctness and relevance to the question.

Database Schema:
{schema_info}

Question: {question}
SQL Query: {sql_query}

IMPORTANT: The query should return actual rows, NOT aggregated results.
For "how many" questions, SELECT * is CORRECT because we want to see the actual data.

Check:
1. Does the query use valid table/column names from the schema?
2. Is the query logically correct for answering the question?
3. Are there any obvious syntax errors?
4. ACCEPT queries that return rows instead of using COUNT(*) - this is the preferred approach

Return JSON with:
{{
    "is_valid": true/false,
    "issues": ["list of any issues found"],
    "suggestions": ["list of suggestions for improvement"]
}}
"""
            
            response = client.chat.completions.create(
                model=os.getenv("AZURE_OPENAI_MODEL"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=300,
                response_format={"type": "json_object"}
            )
            
            verification_result = json.loads(response.choices[0].message.content)
            
            if verification_result.get("is_valid", False):
                return "Query verified successfully."
            else:
                issues = verification_result.get("issues", ["Unknown validation error"])
                return f"Query validation failed: {', '.join(issues)}"
            
        except Exception as e:
            return f"Error verifying query: {str(e)}"
    
    @staticmethod
    def execute_sql_query(sql_query: str, database_path: str) -> str:
        """Tool: Execute SQL query and return results"""
        try:
            # Basic safety check
            if not sql_query.strip().upper().startswith('SELECT'):
                return "Error: Only SELECT queries are allowed"
                
            conn = sqlite3.connect(database_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            
            # Convert to list of dictionaries
            results = [dict(row) for row in rows]
            
            conn.close()
            return json.dumps(results, indent=2)
            
        except Exception as e:
            return f"Error executing query: {str(e)}"
    
    @staticmethod
    def format_response(question: str, sql_query: str, results: str) -> str:
        """Tool: Format results into natural language response"""
        try:
            _load_env()
            AzureOpenAI = _get_openai_client()
            client = AzureOpenAI(
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION")
            )
            
            prompt = f"""
Convert these query results into a natural, conversational response.

Original Question: {question}
SQL Query: {sql_query}
Results: {results}

Provide a clear, helpful answer in natural language that explains the results.
"""
            
            response = client.chat.completions.create(
                model=os.getenv("AZURE_OPENAI_MODEL"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=400
            )
            
            natural_language_answer = response.choices[0].message.content.strip()
            
            # Parse the results for structured output
            try:
                parsed_results = json.loads(results)
            except:
                parsed_results = []
            
            # Return structured object as JSON string
            row_count = len(parsed_results) if isinstance(parsed_results, list) else (1 if parsed_results else 0)
            structured_response = {
                "response": natural_language_answer,
                "sql_query": sql_query,
                "data_results": parsed_results,
                "row_count": row_count
            }
            
            return json.dumps(structured_response, indent=2)
            
        except Exception as e:
            error_response = {
                "response": f"Error formatting response: {str(e)}",
                "sql_query": sql_query,
                "data_results": [],
                "row_count": 0
            }
            return json.dumps(error_response, indent=2)


class NL2SQLAgent:
    """
    Tool-based NL2SQL Agent using Azure OpenAI function calling.
    
    The agent intelligently orchestrates tools to convert natural language
    questions to SQL queries and back to natural language responses.
    """
    
    def __init__(self):
        # Lazy loading - don't create client until needed
        self._client = None
        _load_env()
        self.model = os.getenv("AZURE_OPENAI_MODEL", "gpt-4")
        
        # Map function names to actual functions
        self.function_map = {
            "discover_database_schema": AgentTools.discover_database_schema,
            "generate_sql_query": AgentTools.generate_sql_query,
            "verify_sql_query": AgentTools.verify_sql_query,
            "execute_sql_query": AgentTools.execute_sql_query,
            "format_response": AgentTools.format_response
        }
    
    @property
    def client(self):
        """Lazy-loaded Azure OpenAI client"""
        if self._client is None:
            AzureOpenAI = _get_openai_client()
            self._client = AzureOpenAI(
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION")
            )
        return self._client
    
    @property
    def tools(self):
        """Lazy-loaded tool definitions"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "discover_database_schema",
                    "description": "Discover database schema (tables and columns)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "database_path": {"type": "string", "description": "Path to SQLite database"}
                        },
                        "required": ["database_path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_sql_query",
                    "description": "Generate SQL query from natural language",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {"type": "string", "description": "Natural language question"},
                            "schema_info": {"type": "string", "description": "Database schema information"}
                        },
                        "required": ["question", "schema_info"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "verify_sql_query",
                    "description": "Verify SQL query for correctness and safety",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sql_query": {"type": "string", "description": "SQL query to verify"},
                            "schema_info": {"type": "string", "description": "Database schema information"},
                            "question": {"type": "string", "description": "Original natural language question"}
                        },
                        "required": ["sql_query", "schema_info", "question"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_sql_query",
                    "description": "Execute SQL query and get results",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sql_query": {"type": "string", "description": "SQL query to execute"},
                            "database_path": {"type": "string", "description": "Path to SQLite database"}
                        },
                        "required": ["sql_query", "database_path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "format_response",
                    "description": "Format results into natural language",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {"type": "string", "description": "Original question"},
                            "sql_query": {"type": "string", "description": "SQL query used"},
                            "results": {"type": "string", "description": "Query results"}
                        },
                        "required": ["question", "sql_query", "results"]
                    }
                }
            }
        ]
    
    def process_question(self, question: str, database_path: str, show_logs: bool = True) -> Dict[str, Any]:
        """
        Process a natural language question using the agent with function calling.
        
        Args:
            question: Natural language question
            database_path: Path to SQLite database
            show_logs: Whether to show detailed processing logs
            
        Returns:
            Structured response dictionary
        """
        if show_logs:
            print(f"🚀 STARTING NL2SQL PROCESSING")
            print(f"📝 Question: {question}")
            print(f"🗄️ Database: {database_path}")
            print("=" * 80)
            print("💭 Agent thinking process:")
        
        messages = [
            {
                "role": "system",
                "content": """
You are an intelligent NL2SQL assistant that helps users query databases using natural language.

You have access to these tools:
- discover_database_schema: Learn about database structure
- generate_sql_query: Create SQL queries from natural language  
- verify_sql_query: Validate queries for safety and correctness
- execute_sql_query: Run queries against the database
- format_response: Convert results to natural language

CRITICAL RULE: Your SQL queries must ALWAYS return actual rows (SELECT * FROM table WHERE conditions), 
NEVER use COUNT(*), SUM(), AVG() or other aggregations. The user wants to see the actual data.

You decide which tools to use and when. Use your intelligence to:
1. Understand what information you need
2. Call appropriate tools to gather that information  
3. Generate SQL that returns raw data rows (never aggregated)
4. If verification fails because it expects COUNT(*), regenerate with SELECT * instead
5. Execute queries safely
6. Provide helpful responses

Be intelligent about tool usage - you might need schema info before generating SQL.

IMPORTANT: Always end by calling the format_response tool to provide the final structured response.
"""
            },
            {
                "role": "user", 
                "content": f"Database: {database_path}\nQuestion: {question}"
            }
        ]
        
        # Continue conversation until we have a final answer
        max_iterations = 15
        iteration = 0
        tool_call_count = 0
        final_structured_response = None
        
        while iteration < max_iterations:
            iteration += 1
            
            if show_logs:
                print(f"\n🔄 ITERATION {iteration}")
                print("-" * 40)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                temperature=0.1
            )
            
            message = response.choices[0].message
            messages.append(message)
            
            # If no tool calls, we have the final answer
            if not message.tool_calls:
                if show_logs:
                    print(f"✅ FINAL RESPONSE GENERATED")
                    print(f"📊 Total iterations: {iteration}")
                    print(f"🛠️ Total tool calls: {tool_call_count}")
                    print("-" * 40)
                
                # Return the structured response if we have one, otherwise create a fallback
                if final_structured_response:
                    return final_structured_response
                else:
                    return {
                        "response": message.content,
                        "sql_query": "N/A",
                        "data_results": [],
                        "row_count": 0
                    }
            
            # Execute tool calls with detailed logging
            for tool_call in message.tool_calls:
                tool_call_count += 1
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                if show_logs:
                    print(f"🛠️ TOOL CALL #{tool_call_count}: {function_name}")
                    print(f"📥 Arguments: {function_args}")
                
                # Call the actual function
                start_time = time.time()
                result = self.function_map[function_name](**function_args)
                execution_time = (time.time() - start_time) * 1000
                
                if show_logs:
                    print(f"⏱️ Execution time: {execution_time:.2f}ms")
                    if len(str(result)) > 200:
                        print(f"📤 Result: {str(result)[:200]}...")
                    else:
                        print(f"📤 Result: {result}")
                    print()
                
                # If this was the format_response call, capture the structured response
                if function_name == "format_response":
                    try:
                        final_structured_response = json.loads(result)
                    except:
                        final_structured_response = {
                            "response": result,
                            "sql_query": function_args.get("sql_query", "N/A"),
                            "data_results": [],
                            "row_count": 0
                        }
                
                # Add tool result to conversation
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": str(result)
                })
        
        # Fallback if we reach max iterations
        if final_structured_response:
            return final_structured_response
        else:
            return {
                "response": f"❌ Maximum iterations ({max_iterations}) reached. Unable to complete the request.",
                "sql_query": "N/A",
                "data_results": [],
                "row_count": 0
            }


class AgentDemo:
    """Quick demonstration of the agent"""
    
    @staticmethod
    def run_demo(database_path: str):
        """Run a quick demo of the agent"""
        print("🤖 NL2SQL Agent Demo")
        print("=" * 25)
        
        try:
            agent = NL2SQLAgent()
            
            # Test questions
            test_questions = [
                "How many passengers survived?",
                "What was the survival rate by passenger class?",
                "Who was the oldest passenger?"
            ]
            
            for i, question in enumerate(test_questions, 1):
                print(f"\n--- Demo {i}: {question} ---")
                
                result = agent.process_question(question, database_path, show_logs=False)
                
                print(f"Response: {result['response']}")
                print(f"SQL: {result['sql_query']}")
                print(f"Rows: {result['row_count']}")
            
        except Exception as e:
            print(f"Demo failed: {e}")


if __name__ == "__main__":
    # Run demo
    AgentDemo.run_demo("../outputs/databases/titanic.db")