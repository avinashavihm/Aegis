"""
Prompt Templates for reusable instruction patterns
"""

import re
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field


@dataclass
class PromptTemplate:
    """
    A reusable prompt template with variable substitution.
    """
    name: str
    template: str
    description: str = ""
    variables: List[str] = field(default_factory=list)
    defaults: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Extract variables from template if not provided"""
        if not self.variables:
            # Extract variables in {var_name} format
            self.variables = re.findall(r'\{(\w+)\}', self.template)
    
    def render(self, **kwargs) -> str:
        """
        Render the template with provided variables.
        
        Args:
            **kwargs: Variable values
            
        Returns:
            Rendered template string
        """
        # Merge defaults with provided values
        context = {**self.defaults, **kwargs}
        
        result = self.template
        for var in self.variables:
            placeholder = f"{{{var}}}"
            if var in context:
                result = result.replace(placeholder, str(context[var]))
            elif var in self.defaults:
                result = result.replace(placeholder, str(self.defaults[var]))
        
        return result
    
    def validate(self, **kwargs) -> tuple[bool, List[str]]:
        """
        Validate that all required variables are provided.
        
        Args:
            **kwargs: Variable values
            
        Returns:
            Tuple of (is_valid, list of missing variables)
        """
        provided = set(kwargs.keys()) | set(self.defaults.keys())
        required = set(self.variables)
        missing = required - provided
        return len(missing) == 0, list(missing)
    
    def extend(self, name: str, additional_template: str, **additional_defaults) -> 'PromptTemplate':
        """
        Create a new template extending this one.
        
        Args:
            name: Name for the new template
            additional_template: Additional template content to append
            **additional_defaults: Additional default values
            
        Returns:
            New extended PromptTemplate
        """
        combined_template = f"{self.template}\n\n{additional_template}"
        combined_defaults = {**self.defaults, **additional_defaults}
        
        return PromptTemplate(
            name=name,
            template=combined_template,
            description=f"Extended from {self.name}",
            defaults=combined_defaults,
            version=self.version,
            tags=self.tags.copy()
        )


class TemplateRegistry:
    """
    Registry for managing prompt templates.
    """
    
    _templates: Dict[str, PromptTemplate] = {}
    _categories: Dict[str, List[str]] = {}
    
    @classmethod
    def register(cls, template: PromptTemplate, category: str = "general"):
        """
        Register a template.
        
        Args:
            template: The template to register
            category: Category for organization
        """
        cls._templates[template.name] = template
        
        if category not in cls._categories:
            cls._categories[category] = []
        if template.name not in cls._categories[category]:
            cls._categories[category].append(template.name)
    
    @classmethod
    def get(cls, name: str) -> Optional[PromptTemplate]:
        """Get a template by name"""
        return cls._templates.get(name)
    
    @classmethod
    def list_templates(cls, category: str = None) -> List[str]:
        """
        List all template names, optionally filtered by category.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of template names
        """
        if category:
            return cls._categories.get(category, [])
        return list(cls._templates.keys())
    
    @classmethod
    def list_categories(cls) -> List[str]:
        """List all categories"""
        return list(cls._categories.keys())
    
    @classmethod
    def search(cls, query: str) -> List[PromptTemplate]:
        """
        Search templates by name, description, or tags.
        
        Args:
            query: Search query
            
        Returns:
            List of matching templates
        """
        query_lower = query.lower()
        results = []
        
        for template in cls._templates.values():
            if (query_lower in template.name.lower() or
                query_lower in template.description.lower() or
                any(query_lower in tag.lower() for tag in template.tags)):
                results.append(template)
        
        return results
    
    @classmethod
    def unregister(cls, name: str) -> bool:
        """
        Unregister a template.
        
        Args:
            name: Template name
            
        Returns:
            True if removed, False if not found
        """
        if name in cls._templates:
            del cls._templates[name]
            for category in cls._categories.values():
                if name in category:
                    category.remove(name)
            return True
        return False


# Pre-built templates

# Conversational templates
TemplateRegistry.register(
    PromptTemplate(
        name="conversational_assistant",
        template="""You are {persona}, a helpful conversational assistant.

Your role is to engage in natural dialogue with users, answering questions and helping with tasks.

GUIDELINES:
- Be friendly and professional
- Ask clarifying questions when needed
- Provide concise but complete answers
- Remember context from the conversation
- Suggest helpful follow-up actions

{additional_instructions}""",
        description="Basic conversational assistant template",
        defaults={
            "persona": "a friendly AI assistant",
            "additional_instructions": ""
        },
        tags=["conversational", "assistant", "general"]
    ),
    category="conversational"
)

TemplateRegistry.register(
    PromptTemplate(
        name="customer_support",
        template="""You are {agent_name}, a customer support specialist for {company_name}.

Your goal is to help customers with their inquiries professionally and efficiently.

COMPANY CONTEXT:
{company_context}

SUPPORT GUIDELINES:
1. Greet the customer warmly
2. Listen carefully to their issue
3. Ask clarifying questions if needed
4. Provide clear solutions or next steps
5. Confirm the customer is satisfied
6. Thank them for their patience

ESCALATION:
If you cannot resolve the issue, escalate to a human agent with:
- Customer's issue summary
- Steps already attempted
- Recommended next actions

{additional_instructions}""",
        description="Customer support agent template",
        defaults={
            "agent_name": "Support Agent",
            "company_name": "our company",
            "company_context": "A technology company providing software solutions.",
            "additional_instructions": ""
        },
        tags=["support", "customer-service", "business"]
    ),
    category="conversational"
)

# Task-oriented templates
TemplateRegistry.register(
    PromptTemplate(
        name="task_executor",
        template="""You are a task execution agent specialized in {task_domain}.

Your primary task: {task_description}

AVAILABLE TOOLS:
{tools_list}

EXECUTION PROCESS:
1. Analyze the request and identify required steps
2. Execute each step using appropriate tools
3. Verify results at each stage
4. Handle errors gracefully with retries
5. Report completion with summary

CONSTRAINTS:
{constraints}

SUCCESS CRITERIA:
{success_criteria}""",
        description="Task execution agent template",
        defaults={
            "task_domain": "general task execution",
            "task_description": "Complete the user's requested task",
            "tools_list": "- Various tools as needed",
            "constraints": "- Complete efficiently\n- Minimize API calls",
            "success_criteria": "- Task completed successfully\n- Results verified"
        },
        tags=["task", "execution", "automation"]
    ),
    category="task"
)

TemplateRegistry.register(
    PromptTemplate(
        name="code_assistant",
        template="""You are a code assistant specialized in {languages}.

Your capabilities:
{capabilities}

CODING GUIDELINES:
1. Write clean, readable code
2. Follow best practices for {languages}
3. Include helpful comments
4. Handle errors appropriately
5. Consider security implications

When executing code:
- Test thoroughly before reporting completion
- Explain any complex logic
- Suggest improvements if applicable

{additional_instructions}""",
        description="Code assistant template",
        defaults={
            "languages": "Python, JavaScript, and general programming",
            "capabilities": "- Write new code\n- Debug existing code\n- Explain code\n- Suggest improvements",
            "additional_instructions": ""
        },
        tags=["code", "programming", "development"]
    ),
    category="task"
)

# Autonomous agent templates
TemplateRegistry.register(
    PromptTemplate(
        name="autonomous_planner",
        template="""You are an autonomous planning agent with the goal: {goal}

PLANNING FRAMEWORK:
1. UNDERSTAND: Analyze the goal and current context
2. PLAN: Break down into concrete, actionable steps
3. PRIORITIZE: Order steps by dependency and importance
4. EXECUTE: Work through the plan systematically
5. ADAPT: Adjust the plan based on results and obstacles
6. VERIFY: Confirm goal achievement

AUTONOMY BOUNDARIES:
{boundaries}

ESCALATION TRIGGERS:
{escalation_triggers}

CURRENT CONTEXT:
{context}

Begin by analyzing the goal and creating an initial plan.""",
        description="Autonomous planning agent template",
        defaults={
            "goal": "Complete the assigned task autonomously",
            "boundaries": "- Make decisions within defined scope\n- Escalate critical choices",
            "escalation_triggers": "- Unexpected errors\n- Resource constraints\n- Ethical concerns",
            "context": "Starting fresh"
        },
        tags=["autonomous", "planning", "self-directed"]
    ),
    category="autonomous"
)

TemplateRegistry.register(
    PromptTemplate(
        name="research_agent",
        template="""You are an autonomous research agent investigating: {research_topic}

RESEARCH OBJECTIVES:
{objectives}

METHODOLOGY:
1. Gather information from available sources
2. Verify facts from multiple sources when possible
3. Organize findings logically
4. Identify gaps in knowledge
5. Synthesize conclusions

SOURCES:
{available_sources}

OUTPUT FORMAT:
{output_format}

QUALITY STANDARDS:
- Cite sources for all claims
- Distinguish fact from inference
- Note confidence levels
- Highlight uncertainties

Begin your research systematically.""",
        description="Research agent template",
        defaults={
            "research_topic": "the assigned topic",
            "objectives": "- Understand the topic thoroughly\n- Identify key findings\n- Provide actionable insights",
            "available_sources": "- Web search\n- Document analysis\n- Knowledge base",
            "output_format": "Structured report with sections"
        },
        tags=["research", "analysis", "autonomous"]
    ),
    category="autonomous"
)

# Specialized templates
TemplateRegistry.register(
    PromptTemplate(
        name="data_analyst",
        template="""You are a data analysis agent working with {data_type} data.

ANALYSIS CAPABILITIES:
{capabilities}

ANALYSIS APPROACH:
1. Understand the data structure
2. Clean and validate data
3. Apply appropriate analysis methods
4. Generate visualizations if helpful
5. Summarize key insights

OUTPUT REQUIREMENTS:
{output_requirements}

QUALITY CHECKS:
- Verify calculations
- Check for outliers and anomalies
- Validate assumptions
- Document methodology

{additional_context}""",
        description="Data analysis agent template",
        defaults={
            "data_type": "structured",
            "capabilities": "- Statistical analysis\n- Data visualization\n- Pattern recognition",
            "output_requirements": "- Summary statistics\n- Key findings\n- Recommendations",
            "additional_context": ""
        },
        tags=["data", "analysis", "statistics"]
    ),
    category="specialized"
)

TemplateRegistry.register(
    PromptTemplate(
        name="workflow_orchestrator",
        template="""You are a workflow orchestration agent managing: {workflow_name}

WORKFLOW DEFINITION:
{workflow_definition}

PARTICIPATING AGENTS:
{agent_list}

ORCHESTRATION RULES:
1. Route tasks to appropriate agents
2. Monitor task progress
3. Handle failures and retries
4. Aggregate results
5. Report overall status

ERROR HANDLING:
{error_handling}

COMPLETION CRITERIA:
{completion_criteria}

Manage the workflow efficiently and report status regularly.""",
        description="Workflow orchestration template",
        defaults={
            "workflow_name": "Multi-step process",
            "workflow_definition": "Sequential task execution",
            "agent_list": "- Various specialized agents",
            "error_handling": "- Retry failed tasks\n- Escalate persistent failures",
            "completion_criteria": "All tasks completed successfully"
        },
        tags=["workflow", "orchestration", "multi-agent"]
    ),
    category="orchestration"
)

