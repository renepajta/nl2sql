# 🤖 NL2SQL: Natural Language to SQL Agent

A simple, customer-ready system for converting natural language questions to SQL queries using Azure OpenAI function calling.

## 🚀 Quick Start

### 1. Setup Environment
```bash
# Install dependencies
pip install -r requirements.txt

# Configure Azure OpenAI
echo 'AZURE_OPENAI_ENDPOINT="your-endpoint"' > .env
echo 'AZURE_OPENAI_API_KEY="your-api-key"' >> .env
echo 'AZURE_OPENAI_API_VERSION="2025-04-01-preview"' >> .env
echo 'AZURE_OPENAI_MODEL="gpt-4.1"' >> .env
```

### 2. Prepare Database & Start Chat
```bash
# One command to prepare data and start chat
python -m src.agent_cli --prepare-data --debug

# Or start with existing database
python -m src.agent_cli --db outputs/databases/titanic.db
```

## 💬 Usage

```
🤖 NL2SQL Agent Chat
=========================
📊 Database: titanic: 891 rows, 12 columns

💡 Ready to chat! 🚀

💬 Your question: How many passengers survived?

🎯 342 passengers survived out of 891 total passengers.

📋 Complete Results (342 rows):
  1. {'PassengerId': 1, 'Survived': 1, 'Name': 'Braund, Mr. Owen Harris', ...}
  2. {'PassengerId': 2, 'Survived': 1, 'Name': 'Cumings, Mrs. John Bradley', ...}
  ...

💬 Your question: Who was the oldest passenger?
🎯 The oldest passenger was Mr. Algernon Henry Wilson Barkworth at 80 years old.
```

## 🏗️ How It Works

**Simple Agent Architecture:**
```
Question → Agent (with tools) → SQL → Results → Natural Response
```

**Agent Tools:**
- `discover_database_schema` - Learn database structure
- `generate_sql_query` - Convert NL to SQL  
- `verify_sql_query` - Validate SQL safety
- `execute_sql_query` - Run queries
- `format_response` - Convert results to natural language

**Key Features:**
- ⚡ **Fast startup** - Lazy loading for instant CLI
- 🧠 **Smart agent** - Intelligently orchestrates tools
- 📊 **Complete data** - Always shows actual rows, not just counts
- 🔧 **Debug mode** - See complete agent thinking process
- 💬 **Natural responses** - LLM converts results back to conversation

## 📁 Project Structure

```
├── src/
│   ├── agent.py          # Core NL2SQL agent with tools
│   ├── agent_cli.py      # Interactive chat interface  
│   └── database.py       # Database utilities
├── data/titanic/         # Sample dataset
├── eval/questions.jsonl  # Test cases
└── outputs/databases/    # Generated databases
```

## 🎯 Commands

| Command | Description |
|---------|-------------|
| `help` | Show commands |
| `history` | Recent questions |
| `stats` | Session statistics |
| `debug` | Toggle debug mode (see agent thinking) |
| `clear` | Clear history |
| `quit` | Exit |

## 🔧 Configuration

Create `.env` file with your Azure OpenAI credentials:

```bash
AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
AZURE_OPENAI_API_KEY="your-api-key"  
AZURE_OPENAI_API_VERSION="2025-04-01-preview"
AZURE_OPENAI_MODEL="gpt-4.1"
```

## 🧪 Testing

```bash
# Test individual components
python -m src.agent      # Test agent tools
python -m src.database   # Test database utilities

# Interactive testing
python -m src.agent_cli --db outputs/databases/titanic.db --debug
```

## ✨ Customer Benefits

- **Simple Setup** - One command to get started
- **Natural Interface** - Ask questions in plain English
- **Complete Transparency** - See actual data rows and SQL queries
- **Easy Experimentation** - Debug mode shows agent reasoning
- **Ready for Any Database** - Just point to your SQLite file

Perfect for demonstrating NL2SQL capabilities and experimenting with different question types!