# Aegis: Simplified LLM Agent Framework

Aegis is a simplified but feature-complete LLM agent framework that provides natural language-driven agent creation, multi-agent orchestration, and workflow management.

## 🚀 Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the project root with your API keys:

```bash
# Copy the template
cp .env.template .env

# Edit .env and add your API keys
```

**Required API Keys** (at least one):
- `OPENAI_API_KEY` - For OpenAI models (GPT-4, GPT-3.5)
- `ANTHROPIC_API_KEY` - For Anthropic models (Claude)
- `GEMINI_API_KEY` - For Google Gemini models
- `GROQ_API_KEY` - For Groq models
- `DEEPSEEK_API_KEY` - For DeepSeek models
- `HUGGINGFACE_API_KEY` - For HuggingFace models

**Optional Configuration:**
```bash
# Model selection (default: gemini-2.0-flash)
COMPLETION_MODEL=gpt-4o

# Workspace directory (default: workspace)
WORKSPACE_DIR=workspace

# Debug mode (default: false)
DEBUG=false

# Function calling (default: true)
FN_CALL=true
```

### 3. Run Aegis

```bash
python main.py
```

## 📖 Usage Guide

### Main Menu

When you run `python main.py`, you'll see a menu with three modes:

1. **User Mode** - Multi-agent research assistant
2. **Agent Editor** - Create and manage agents
3. **Workflow Editor** - Create and manage workflows

### User Mode

In User Mode, you interact with a multi-agent system:

- **System Triage Agent**: Routes your requests to specialized agents
- **File Agent**: Handles file operations (read, write, search)
- **Web Agent**: Handles web browsing and content extraction
- **Code Agent**: Executes Python code and shell commands

**Example:**
```
You: Read the file README.md and summarize it
```

The System Triage Agent will route this to the File Agent, which will read and summarize the file.

### Agent Editor Mode

Create custom agents through natural language conversation:

1. Select "Agent Editor" from the main menu
2. Describe the agent you want to create
3. The Agent Editor will generate the agent code
4. Test and refine your agent

**Example:**
```
You: Create an agent that can analyze CSV files and generate reports
```

### Workflow Editor Mode

Create workflows that chain multiple agents together:

1. Select "Workflow Editor" from the main menu
2. Describe the workflow you want to create
3. The Workflow Editor will generate the workflow code
4. Execute your workflow

## 🛠️ Available Tools

### File Tools
- `read_file` - Read file contents
- `write_file` - Write to files
- `list_files` - List directory contents
- `search_files` - Search for files

### Web Tools
- `fetch_url` - Fetch web page content
- `search_web` - Search the web
- `extract_content` - Extract content from HTML

### Code Tools
- `execute_python` - Execute Python code
- `execute_command` - Run shell commands
- `run_script` - Run Python scripts

### Terminal Tools
- `run_command` - Execute terminal commands
- `list_directory` - List directory contents
- `create_file` - Create files
- `create_directory` - Create directories

## 📝 Examples

### Example 1: File Analysis

```
You: Read all Python files in the current directory and list their functions
```

### Example 2: Web Research

```
You: Search for information about Python async programming and save it to a file
```

### Example 3: Code Execution

```
You: Write a Python script that calculates fibonacci numbers and run it
```

## 🔧 Advanced Configuration

### Using Different Models

Set the `COMPLETION_MODEL` environment variable:

```bash
# OpenAI
COMPLETION_MODEL=gpt-4o python main.py

# Anthropic (default)
COMPLETION_MODEL=claude-3-5-sonnet-20241022 python main.py

# Gemini
COMPLETION_MODEL=gemini/gemini-2.0-flash python main.py

# Groq
COMPLETION_MODEL=groq/deepseek-r1-distill-llama-70b python main.py
```

### Custom Workspace

```bash
WORKSPACE_DIR=/path/to/workspace python main.py
```

### Debug Mode

```bash
DEBUG=true python main.py
```

## 🐛 Troubleshooting

### Authentication Errors

If you see authentication errors:
1. Check that your `.env` file exists and contains valid API keys
2. Verify the API key format (no extra spaces or quotes)
3. Ensure the API key has sufficient credits/permissions

### Model Not Found

If a model isn't available:
1. Check that the model name is correct
2. Verify your API key has access to that model
3. Try a different model provider

### Import Errors

If you see import errors:
1. Ensure all dependencies are installed: `pip install -r requirements.txt`
2. Check that you're using Python 3.10, 3.11, or 3.12
3. Verify your virtual environment is activated

## 📚 Architecture

Aegis consists of:

- **Core Engine** (`aegis/core.py`) - Main orchestration engine
- **Registry** (`aegis/registry.py`) - Central registry for tools, agents, workflows
- **Agents** (`aegis/agents/`) - System and meta agents
- **Tools** (`aegis/tools/`) - Core and meta tools
- **Environment** (`aegis/environment/`) - Local execution environments
- **CLI** (`aegis/cli/`) - Command-line interface

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

[Add your license here]

## 🙏 Acknowledgments

Aegis is inspired by [AutoAgent](https://github.com/HKUDS/AutoAgent) and simplified for easier use and deployment.

