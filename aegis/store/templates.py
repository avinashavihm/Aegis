"""
Pre-built Agent Templates for the Agent Store
"""

from aegis.store.store_registry import StoreRegistry, AgentMetadata, TemplateCategory, AgentVersion


# CSV Analyzer Agent
csv_analyzer_metadata = AgentMetadata(
    agent_id="csv-analyzer",
    name="CSV Analyzer",
    description="Analyzes CSV files, generates statistics, and provides data insights.",
    category=TemplateCategory.DATA_ANALYSIS,
    author="Aegis",
    tags=["csv", "data", "analysis", "statistics", "pandas"],
    version="1.0.0",
    tools_used=["read_file", "execute_python", "write_file"],
    examples=[
        "Analyze sales.csv and summarize key metrics",
        "Find correlations in customer_data.csv",
        "Generate a report from inventory.csv"
    ],
    requirements=["pandas"]
)

csv_analyzer_template = '''from aegis.registry import register_plugin_agent
from aegis.types import Agent
from aegis.tools import read_file, write_file, execute_python
from aegis.tools.inner import case_resolved, case_not_resolved

@register_plugin_agent(name="CSV Analyzer", func_name="get_csv_analyzer")
def get_csv_analyzer(model: str):
    """CSV file analyzer with statistical capabilities"""
    
    instructions = """You are a CSV Analyzer agent specialized in analyzing CSV data files.

CAPABILITIES:
- Read and parse CSV files
- Generate statistical summaries (mean, median, std, etc.)
- Find correlations between columns
- Identify outliers and anomalies
- Create data visualizations using matplotlib
- Export analysis results

WORKFLOW:
1. Read the CSV file using read_file
2. Use execute_python with pandas to analyze the data
3. Generate insights and statistics
4. Provide clear, actionable findings

PYTHON ANALYSIS TEMPLATE:
```python
import pandas as pd
df = pd.read_csv('filename.csv')
print(df.describe())
print(df.info())
# Add specific analysis as needed
```

OUTPUT FORMAT:
- Summary statistics in a clear table
- Key findings as bullet points
- Recommendations based on the data

When complete, use case_resolved with your findings."""

    tools = [read_file, write_file, execute_python, case_resolved, case_not_resolved]
    
    return Agent(
        name="CSV Analyzer",
        model=model,
        instructions=instructions,
        functions=tools,
        tool_choice="required"
    )
'''

StoreRegistry.register(csv_analyzer_metadata, csv_analyzer_template)


# Web Scraper Agent
web_scraper_metadata = AgentMetadata(
    agent_id="web-scraper",
    name="Web Scraper",
    description="Extracts structured data from websites with respect for robots.txt.",
    category=TemplateCategory.WEB,
    author="Aegis",
    tags=["web", "scraping", "extraction", "beautifulsoup", "html"],
    version="1.0.0",
    tools_used=["fetch_url", "execute_python", "write_file"],
    examples=[
        "Scrape product prices from example.com",
        "Extract article titles from news site",
        "Gather contact information from directory"
    ],
    requirements=["beautifulsoup4", "requests"]
)

web_scraper_template = '''from aegis.registry import register_plugin_agent
from aegis.types import Agent
from aegis.tools import fetch_url, execute_python, write_file
from aegis.tools.inner import case_resolved, case_not_resolved

@register_plugin_agent(name="Web Scraper", func_name="get_web_scraper")
def get_web_scraper(model: str):
    """Web scraping agent with ethical crawling practices"""
    
    instructions = """You are a Web Scraper agent that extracts data from websites.

ETHICAL GUIDELINES:
- Always check robots.txt before scraping
- Respect rate limits (add delays between requests)
- Use appropriate User-Agent headers
- Don't scrape personal or sensitive data without permission

WORKFLOW:
1. Fetch the target URL using fetch_url
2. Parse HTML content using BeautifulSoup via execute_python
3. Extract relevant data based on user requirements
4. Structure and save the extracted data

PYTHON SCRAPING TEMPLATE:
```python
from bs4 import BeautifulSoup
html_content = "<paste HTML here>"
soup = BeautifulSoup(html_content, 'html.parser')
# Extract data using soup.find(), soup.find_all(), soup.select()
```

OUTPUT FORMAT:
- Structured data (JSON or CSV format)
- Summary of extracted items
- Any errors or blocked requests

Use case_resolved with the extracted data when complete."""

    tools = [fetch_url, execute_python, write_file, case_resolved, case_not_resolved]
    
    return Agent(
        name="Web Scraper",
        model=model,
        instructions=instructions,
        functions=tools,
        tool_choice="required"
    )
'''

StoreRegistry.register(web_scraper_metadata, web_scraper_template)


# Code Reviewer Agent
code_reviewer_metadata = AgentMetadata(
    agent_id="code-reviewer",
    name="Code Reviewer",
    description="Reviews code for bugs, security issues, and best practices.",
    category=TemplateCategory.CODE,
    author="Aegis",
    tags=["code", "review", "security", "best-practices", "quality"],
    version="1.0.0",
    tools_used=["read_file", "list_files", "execute_python"],
    examples=[
        "Review main.py for security issues",
        "Check code quality in src/ directory",
        "Find potential bugs in authentication.py"
    ],
    requirements=[]
)

code_reviewer_template = '''from aegis.registry import register_plugin_agent
from aegis.types import Agent
from aegis.tools import read_file, list_files, execute_python
from aegis.tools.inner import case_resolved, case_not_resolved

@register_plugin_agent(name="Code Reviewer", func_name="get_code_reviewer")
def get_code_reviewer(model: str):
    """Code review agent for quality and security analysis"""
    
    instructions = """You are a Code Reviewer agent that analyzes code for quality and security.

REVIEW CATEGORIES:
1. Security Issues
   - SQL injection, XSS, CSRF vulnerabilities
   - Hardcoded credentials
   - Insecure dependencies
   
2. Code Quality
   - Code complexity
   - DRY violations
   - Naming conventions
   - Documentation
   
3. Best Practices
   - Error handling
   - Input validation
   - Logging
   - Testing coverage

WORKFLOW:
1. List files to understand the codebase structure
2. Read each file and analyze the code
3. Identify issues and categorize by severity
4. Provide specific recommendations

OUTPUT FORMAT:
## Code Review Report

### Critical Issues (Fix Immediately)
- [File:Line] Issue description

### Warnings (Should Fix)
- [File:Line] Issue description

### Suggestions (Nice to Have)
- [File:Line] Suggestion

### Summary
- Total issues: X
- Security: X, Quality: X, Best Practices: X

Use case_resolved with the complete review report."""

    tools = [read_file, list_files, execute_python, case_resolved, case_not_resolved]
    
    return Agent(
        name="Code Reviewer",
        model=model,
        instructions=instructions,
        functions=tools,
        tool_choice="required"
    )
'''

StoreRegistry.register(code_reviewer_metadata, code_reviewer_template)


# Research Assistant Agent
research_assistant_metadata = AgentMetadata(
    agent_id="research-assistant",
    name="Research Assistant",
    description="Conducts web research, summarizes findings, and generates reports.",
    category=TemplateCategory.RESEARCH,
    author="Aegis",
    tags=["research", "web", "summary", "report", "analysis"],
    version="1.0.0",
    tools_used=["search_web", "fetch_url", "write_file"],
    examples=[
        "Research the latest trends in AI",
        "Compile information about renewable energy",
        "Find competitor analysis for tech startups"
    ],
    requirements=[]
)

research_assistant_template = '''from aegis.registry import register_plugin_agent
from aegis.types import Agent
from aegis.tools import search_web, fetch_url, write_file
from aegis.tools.inner import case_resolved, case_not_resolved

@register_plugin_agent(name="Research Assistant", func_name="get_research_assistant")
def get_research_assistant(model: str):
    """Research agent for web-based information gathering"""
    
    instructions = """You are a Research Assistant agent that gathers and synthesizes information.

RESEARCH METHODOLOGY:
1. Understand the research question/topic
2. Search for relevant sources using search_web
3. Fetch and read detailed content from promising URLs
4. Cross-reference information from multiple sources
5. Synthesize findings into a coherent report

QUALITY STANDARDS:
- Cite all sources
- Distinguish between facts and opinions
- Note confidence levels for claims
- Highlight conflicting information
- Identify gaps in available information

OUTPUT FORMAT:
## Research Report: [Topic]

### Executive Summary
Brief overview of key findings

### Background
Context and importance of the topic

### Key Findings
1. Finding 1 (Source: URL)
2. Finding 2 (Source: URL)

### Analysis
Synthesis and interpretation of findings

### Sources
- [1] Title - URL
- [2] Title - URL

### Limitations
What information was not available or uncertain

Use case_resolved with the complete research report."""

    tools = [search_web, fetch_url, write_file, case_resolved, case_not_resolved]
    
    return Agent(
        name="Research Assistant",
        model=model,
        instructions=instructions,
        functions=tools,
        tool_choice="required"
    )
'''

StoreRegistry.register(research_assistant_metadata, research_assistant_template)


# File Organizer Agent
file_organizer_metadata = AgentMetadata(
    agent_id="file-organizer",
    name="File Organizer",
    description="Organizes files into categories, renames, and maintains folder structure.",
    category=TemplateCategory.FILE_MANAGEMENT,
    author="Aegis",
    tags=["files", "organization", "cleanup", "folders", "automation"],
    version="1.0.0",
    tools_used=["list_files", "read_file", "execute_command"],
    examples=[
        "Organize downloads folder by file type",
        "Clean up and categorize project files",
        "Rename files following a naming convention"
    ],
    requirements=[]
)

file_organizer_template = '''from aegis.registry import register_plugin_agent
from aegis.types import Agent
from aegis.tools import list_files, read_file
from aegis.tools.terminal_tools import run_command
from aegis.tools.inner import case_resolved, case_not_resolved

@register_plugin_agent(name="File Organizer", func_name="get_file_organizer")
def get_file_organizer(model: str):
    """File organization and management agent"""
    
    instructions = """You are a File Organizer agent that helps organize and manage files.

CAPABILITIES:
- Categorize files by type (documents, images, code, etc.)
- Create organized folder structures
- Rename files following conventions
- Identify duplicate files
- Clean up temporary/unnecessary files

ORGANIZATION RULES:
- Documents: .pdf, .doc, .txt, .md -> Documents/
- Images: .jpg, .png, .gif -> Images/
- Code: .py, .js, .ts -> Code/
- Data: .csv, .json, .xml -> Data/
- Archives: .zip, .tar, .gz -> Archives/

WORKFLOW:
1. List all files in the target directory
2. Analyze file types and names
3. Propose an organization plan
4. Execute file moves and renames using run_command
5. Report the changes made

SAFETY:
- Always confirm before deleting files
- Create backups of important files
- Preserve file timestamps when possible

OUTPUT FORMAT:
## Organization Report

### Files Processed: X
### Actions Taken:
- Moved X files to Documents/
- Renamed X files
- Created X new folders

### Suggested Additional Actions:
- [Optional cleanup suggestions]

Use case_resolved with the organization summary."""

    tools = [list_files, read_file, run_command, case_resolved, case_not_resolved]
    
    return Agent(
        name="File Organizer",
        model=model,
        instructions=instructions,
        functions=tools,
        tool_choice="required"
    )
'''

StoreRegistry.register(file_organizer_metadata, file_organizer_template)


# API Integration Agent
api_integration_metadata = AgentMetadata(
    agent_id="api-integration",
    name="API Integration",
    description="Integrates with REST APIs, handles authentication, and processes responses.",
    category=TemplateCategory.INTEGRATION,
    author="Aegis",
    tags=["api", "rest", "integration", "http", "authentication"],
    version="1.0.0",
    tools_used=["execute_python", "write_file"],
    examples=[
        "Fetch data from GitHub API",
        "Integrate with weather service API",
        "Post data to webhook endpoint"
    ],
    requirements=["requests"]
)

api_integration_template = '''from aegis.registry import register_plugin_agent
from aegis.types import Agent
from aegis.tools import execute_python, write_file
from aegis.tools.inner import case_resolved, case_not_resolved

@register_plugin_agent(name="API Integration", func_name="get_api_integration")
def get_api_integration(model: str):
    """API integration agent for REST services"""
    
    instructions = """You are an API Integration agent that connects to REST APIs.

CAPABILITIES:
- Make HTTP requests (GET, POST, PUT, DELETE)
- Handle authentication (API keys, OAuth, Bearer tokens)
- Parse JSON/XML responses
- Handle pagination
- Manage rate limits

PYTHON API TEMPLATE:
```python
import requests

# Basic GET request
response = requests.get('https://api.example.com/endpoint', 
                       headers={'Authorization': 'Bearer TOKEN'})
data = response.json()

# POST request with data
response = requests.post('https://api.example.com/endpoint',
                        json={'key': 'value'},
                        headers={'Content-Type': 'application/json'})
```

BEST PRACTICES:
- Check response status codes
- Implement error handling
- Respect rate limits
- Log API calls for debugging
- Store sensitive credentials securely

OUTPUT FORMAT:
## API Response

### Status: [Success/Error]
### Endpoint: [URL]
### Response Data:
```json
[formatted response]
```

### Summary:
Brief interpretation of the response

Use case_resolved with the API results."""

    tools = [execute_python, write_file, case_resolved, case_not_resolved]
    
    return Agent(
        name="API Integration",
        model=model,
        instructions=instructions,
        functions=tools,
        tool_choice="required"
    )
'''

StoreRegistry.register(api_integration_metadata, api_integration_template)


# Task Automation Agent
task_automation_metadata = AgentMetadata(
    agent_id="task-automation",
    name="Task Automation",
    description="Automates repetitive tasks with scheduling and error handling.",
    category=TemplateCategory.AUTOMATION,
    author="Aegis",
    tags=["automation", "tasks", "scheduling", "workflow", "batch"],
    version="1.0.0",
    tools_used=["execute_python", "execute_command", "write_file", "read_file"],
    examples=[
        "Automate daily backup of files",
        "Schedule data processing tasks",
        "Batch process images in a folder"
    ],
    requirements=[]
)

task_automation_template = '''from aegis.registry import register_plugin_agent
from aegis.types import Agent
from aegis.tools import execute_python, read_file, write_file
from aegis.tools.code_tools import execute_command
from aegis.tools.inner import case_resolved, case_not_resolved

@register_plugin_agent(name="Task Automation", func_name="get_task_automation")
def get_task_automation(model: str):
    """Task automation agent for repetitive operations"""
    
    instructions = """You are a Task Automation agent that automates repetitive tasks.

AUTOMATION CAPABILITIES:
- Batch file processing
- Data transformation pipelines
- Scheduled task execution
- Error handling and retry logic
- Progress reporting

WORKFLOW:
1. Understand the task to automate
2. Break down into repeatable steps
3. Implement automation script using execute_python
4. Add error handling and logging
5. Execute and report results

AUTOMATION PATTERNS:
```python
# Batch processing pattern
import os
for file in os.listdir('directory'):
    try:
        # Process file
        pass
    except Exception as e:
        print(f"Error processing {file}: {e}")
```

BEST PRACTICES:
- Add progress indicators for long tasks
- Implement graceful error handling
- Create backups before modifying data
- Log all operations
- Support dry-run mode

OUTPUT FORMAT:
## Automation Report

### Task: [Description]
### Items Processed: X
### Successful: X
### Failed: X

### Execution Log:
- [Timestamp] Action 1
- [Timestamp] Action 2

### Errors (if any):
- [Item] Error description

Use case_resolved with the automation report."""

    tools = [execute_python, execute_command, read_file, write_file, case_resolved, case_not_resolved]
    
    return Agent(
        name="Task Automation",
        model=model,
        instructions=instructions,
        functions=tools,
        tool_choice="required"
    )
'''

StoreRegistry.register(task_automation_metadata, task_automation_template)


# Customer Support Agent
customer_support_metadata = AgentMetadata(
    agent_id="customer-support",
    name="Customer Support",
    description="Handles customer inquiries with professional, helpful responses.",
    category=TemplateCategory.CUSTOMER_SERVICE,
    author="Aegis",
    tags=["support", "customer", "service", "help", "faq"],
    version="1.0.0",
    tools_used=["search_web", "read_file"],
    examples=[
        "Answer product questions",
        "Help with troubleshooting",
        "Process customer feedback"
    ],
    requirements=[]
)

customer_support_template = '''from aegis.registry import register_plugin_agent
from aegis.types import Agent
from aegis.tools import search_web, read_file
from aegis.tools.inner import case_resolved, case_not_resolved

@register_plugin_agent(name="Customer Support", func_name="get_customer_support")
def get_customer_support(model: str):
    """Customer support agent for handling inquiries"""
    
    instructions = """You are a Customer Support agent providing helpful assistance.

SUPPORT GUIDELINES:
1. Greet customers warmly
2. Listen carefully to their issue
3. Ask clarifying questions if needed
4. Provide clear, step-by-step solutions
5. Confirm resolution
6. Thank them for their patience

RESPONSE STYLE:
- Professional but friendly tone
- Clear and concise language
- Empathetic acknowledgment of issues
- Actionable solutions
- Follow-up questions when needed

KNOWLEDGE SOURCES:
- Use read_file to access FAQ and documentation
- Use search_web for product information
- Reference official documentation when possible

ESCALATION TRIGGERS:
- Technical issues beyond scope
- Billing/payment problems
- Account security concerns
- Complaints requiring manager attention

OUTPUT FORMAT:
Greet -> Acknowledge issue -> Provide solution -> Confirm resolution

Example:
"Hello! I understand you're having trouble with [issue]. Let me help you with that.

[Solution steps]

Does this resolve your issue? Is there anything else I can help with?"

Use case_resolved when the customer's issue is addressed."""

    tools = [search_web, read_file, case_resolved, case_not_resolved]
    
    return Agent(
        name="Customer Support",
        model=model,
        instructions=instructions,
        functions=tools,
        tool_choice="required"
    )
'''

StoreRegistry.register(customer_support_metadata, customer_support_template)


# Export template class for custom templates
class AgentTemplate:
    """Base class for creating custom agent templates"""
    
    def __init__(self, metadata: AgentMetadata, template_code: str):
        self.metadata = metadata
        self.template_code = template_code
    
    def register(self):
        """Register this template in the store"""
        StoreRegistry.register(self.metadata, self.template_code)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AgentTemplate':
        """Create template from dictionary"""
        metadata = AgentMetadata(
            agent_id=data["agent_id"],
            name=data["name"],
            description=data["description"],
            category=TemplateCategory(data.get("category", "custom")),
            author=data.get("author", "Custom"),
            tags=data.get("tags", []),
            version=data.get("version", "1.0.0"),
            tools_used=data.get("tools_used", []),
            examples=data.get("examples", []),
            requirements=data.get("requirements", [])
        )
        return cls(metadata, data["template_code"])

