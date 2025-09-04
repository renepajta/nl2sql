"""
Agent-Based CLI Chat Interface

Interactive chat interface using the tool-based NL2SQL agent.
Simple, continuous conversation for testing various questions.
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, Any
import readline

from .agent import NL2SQLAgent
from .database import DataPreparation


class AgentChat:
    """
    Interactive chat interface using the NL2SQL agent.
    
    Provides continuous conversation capability for testing
    various questions and prompt experimentation.
    """
    
    def __init__(self, database_path: str, debug: bool = False):
        self.database_path = database_path
        self.agent = None  # Lazy load agent
        self.debug = debug
        self.conversation_history = []
        self.session_stats = {
            "questions_asked": 0,
            "successful_queries": 0,
            "total_tokens": 0,
            "avg_response_time": 0.0
        }
    
    def _get_agent(self):
        """Lazy-load the agent when first needed"""
        if self.agent is None:
            print("🔧 Initializing NL2SQL agent...")
            self.agent = NL2SQLAgent()
        return self.agent
    
    def start_chat(self):
        """Start the interactive chat session"""
        print("🤖 NL2SQL Agent Chat")
        print("=" * 25)
        print("Ask me questions about your database in natural language!")
        print("The agent will intelligently use tools to answer your questions.")
        print("Type 'help' for commands or 'quit' to exit.\n")
        
        # Show database info quickly
        self._show_database_info()
        
        print("\n💡 Ready to chat! The agent will initialize on your first question.")
        print("This provides faster startup time. 🚀")
        
        while True:
            try:
                # Get user input
                user_input = input("\n💬 Your question: ").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    self._show_session_stats()
                    break
                elif user_input.lower() == 'help':
                    self._show_help()
                    continue
                elif user_input.lower() == 'history':
                    self._show_history()
                    continue
                elif user_input.lower() == 'stats':
                    self._show_session_stats()
                    continue
                elif user_input.lower() == 'debug':
                    self.debug = not self.debug
                    print(f"🔧 Debug mode: {'ON' if self.debug else 'OFF'}")
                    continue
                elif user_input.lower() == 'clear':
                    self.conversation_history.clear()
                    print("🗑️ Conversation history cleared")
                    continue
                
                # Process question
                self._process_question(user_input)
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                self._show_session_stats()
                break
            except Exception as e:
                print(f"\n❌ Unexpected error: {e}")
                if self.debug:
                    import traceback
                    traceback.print_exc()
    
    def _process_question(self, question: str):
        """Process a single question through the agent"""
        import time
        start_time = time.time()
        
        self.session_stats["questions_asked"] += 1
        
        print(f"\n🔄 Processing your question...")
        if not self.debug:
            print("💭 Agent is thinking... (use 'debug' command to see detailed tool execution)")
        
        try:
            # Get agent (lazy loaded)
            agent = self._get_agent()
            
            # Process with agent - always show logs for thinking process
            result = agent.process_question(
                question, 
                self.database_path, 
                show_logs=True  # Always show thinking process
            )
            
            processing_time = time.time() - start_time
            
            # Update stats
            if "error" not in result.get("response", "").lower():
                self.session_stats["successful_queries"] += 1
            
            # Update average response time
            total_questions = self.session_stats["questions_asked"]
            current_avg = self.session_stats["avg_response_time"]
            self.session_stats["avg_response_time"] = (
                (current_avg * (total_questions - 1) + processing_time) / total_questions
            )
            
            # Store in history
            history_entry = {
                "question": question,
                "response": result.get("response", ""),
                "sql_query": result.get("sql_query", ""),
                "row_count": result.get("row_count", 0),
                "processing_time": processing_time,
                "timestamp": time.strftime("%H:%M:%S")
            }
            self.conversation_history.append(history_entry)
            
            # Display result
            print(f"\n🎯 {result.get('response', 'No response generated')}")
            
            # Always show query details and complete data
            print(f"\n📊 Query Details:")
            print(f"  • SQL: {result.get('sql_query', 'N/A')}")
            print(f"  • Rows returned: {result.get('row_count', 0)}")
            print(f"  • Processing time: {processing_time:.2f}s")
            
            # Show actual data results - complete list
            data_results = result.get("data_results", [])
            if data_results and len(data_results) > 0:
                row_count = len(data_results) if isinstance(data_results, list) else 1
                print(f"\n📋 Complete Results ({row_count} rows):")
                
                # Handle different result types
                if isinstance(data_results, list):
                    for i, row in enumerate(data_results, 1):
                        if isinstance(row, dict):
                            print(f"  {i}. {row}")
                        else:
                            print(f"  {i}. {str(row)}")
                        if i >= 20:  # Show up to 20 rows
                            remaining = row_count - 20
                            if remaining > 0:
                                print(f"  ... and {remaining} more rows")
                            break
                else:
                    print(f"  1. {data_results}")
            else:
                print(f"\n📋 No matching data found")
            
        except Exception as e:
            print(f"\n❌ Error processing question: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
    
    def _show_database_info(self):
        """Show basic database information"""
        try:
            db_path = Path(self.database_path)
            if not db_path.exists():
                print(f"⚠️ Database not found: {self.database_path}")
                return
            
            print(f"📊 Database: {self.database_path}")
            print(f"📁 Size: {db_path.stat().st_size / 1024:.1f} KB")
            
            # Quick schema check
            import sqlite3
            conn = sqlite3.connect(self.database_path)
            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            conn.close()
            
            print(f"📋 Tables: {', '.join([t[0] for t in tables])}")
            
        except Exception as e:
            print(f"⚠️ Could not load database info: {e}")
    
    def _show_help(self):
        """Show help information"""
        print("""
🆘 Available Commands:
  • Type any question in natural language
  • 'help' - Show this help
  • 'history' - Show recent questions and responses  
  • 'stats' - Show session statistics
  • 'debug' - Toggle debug mode (shows tool calls)
  • 'clear' - Clear conversation history
  • 'quit' - Exit chat

💡 Example Questions:
  • "How many passengers survived?"
  • "What was the survival rate by class?"
  • "Show me passengers with cabins starting with 'B'"
  • "Find the average age of female passengers"
  • "Who had the highest fare in first class?"

🔧 Debug Mode:
  Toggle debug mode to see detailed tool execution logs,
  including schema discovery, SQL generation, validation, and execution.
        """)
    
    def _show_history(self):
        """Show conversation history"""
        if not self.conversation_history:
            print("📝 No questions asked yet.")
            return
        
        print(f"📝 Conversation History ({len(self.conversation_history)} questions):")
        
        for i, entry in enumerate(self.conversation_history[-5:], 1):  # Last 5
            print(f"\n  {i}. [{entry['timestamp']}] {entry['question']}")
            print(f"     💬 {entry['response'][:80]}{'...' if len(entry['response']) > 80 else ''}")
            print(f"     📊 {entry['row_count']} rows, ⏱️ {entry['processing_time']:.1f}s")
            if self.debug and entry['sql_query'] != "N/A":
                print(f"     🔧 SQL: {entry['sql_query'][:60]}{'...' if len(entry['sql_query']) > 60 else ''}")
    
    def _show_session_stats(self):
        """Show session statistics"""
        stats = self.session_stats
        success_rate = (stats["successful_queries"] / stats["questions_asked"] * 100) if stats["questions_asked"] > 0 else 0
        
        print(f"\n📊 Session Statistics:")
        print(f"  • Questions asked: {stats['questions_asked']}")
        print(f"  • Successful queries: {stats['successful_queries']} ({success_rate:.1f}%)")
        print(f"  • Average response time: {stats['avg_response_time']:.2f}s")
        print(f"  • Conversation entries: {len(self.conversation_history)}")


def main():
    """Main CLI entry point for agent-based chat"""
    parser = argparse.ArgumentParser(
        description="NL2SQL Agent Chat Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.agent_cli --db outputs/databases/titanic.db
  python -m src.agent_cli --prepare-data --db-output outputs/databases/titanic.db --debug
  python -m src.agent_cli --db outputs/databases/titanic.db --debug
        """
    )
    
    parser.add_argument(
        "--db", 
        type=str, 
        help="Path to SQLite database file"
    )
    parser.add_argument(
        "--prepare-data", 
        action="store_true", 
        help="Prepare Titanic database before starting chat"
    )
    parser.add_argument(
        "--data-dir", 
        type=str, 
        default="data/titanic",
        help="Directory containing CSV data files (default: data/titanic)"
    )
    parser.add_argument(
        "--db-output", 
        type=str, 
        default="outputs/databases/titanic.db",
        help="Output database path (default: outputs/databases/titanic.db)"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable debug mode (shows tool execution details)"
    )
    
    args = parser.parse_args()
    
    # Data preparation mode
    if args.prepare_data:
        print("🔧 Preparing database...")
        try:
            db_path = DataPreparation.prepare_titanic_database(
                data_dir=args.data_dir,
                output_dir=str(Path(args.db_output).parent)
            )
            print(f"✅ Database prepared: {db_path}")
            
            if not args.db:
                args.db = db_path
                
        except Exception as e:
            print(f"❌ Data preparation failed: {e}")
            return 1
    
    # Validate database path
    if not args.db:
        print("❌ Database path required. Use --db or --prepare-data")
        parser.print_help()
        return 1
    
    db_path = Path(args.db)
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        print("Use --prepare-data to create database or check path")
        return 1
    
    # Start agent chat
    try:
        chat = AgentChat(str(db_path), debug=args.debug)
        chat.start_chat()
        
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Chat failed: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())