"""
Instruction Builder for creating structured agent instructions
"""

from typing import Dict, List, Optional, Any, Union
from aegis.types import StructuredInstruction, OutputFormat


class InstructionBuilder:
    """
    Builder for creating structured instructions for agents.
    Supports fluent API for easy instruction composition.
    """
    
    def __init__(self, base_prompt: str = ""):
        """
        Initialize the instruction builder.
        
        Args:
            base_prompt: The base prompt/instruction text
        """
        self._base_prompt = base_prompt
        self._formatting_rules: Dict[str, str] = {}
        self._output_format = OutputFormat.TEXT
        self._output_schema: Optional[Dict[str, Any]] = None
        self._constraints: List[str] = []
        self._examples: List[Dict[str, str]] = []
        self._variables: Dict[str, Any] = {}
        self._sections: List[Dict[str, str]] = []
        self._parent: Optional['InstructionBuilder'] = None
    
    def set_base_prompt(self, prompt: str) -> 'InstructionBuilder':
        """Set the base prompt text"""
        self._base_prompt = prompt
        return self
    
    def add_section(self, title: str, content: str) -> 'InstructionBuilder':
        """
        Add a titled section to the instructions.
        
        Args:
            title: Section title
            content: Section content
        """
        self._sections.append({"title": title, "content": content})
        return self
    
    def add_formatting_rule(self, name: str, description: str) -> 'InstructionBuilder':
        """
        Add a formatting rule.
        
        Args:
            name: Rule name
            description: Rule description
        """
        self._formatting_rules[name] = description
        return self
    
    def set_output_format(self, format_type: Union[OutputFormat, str]) -> 'InstructionBuilder':
        """
        Set the output format.
        
        Args:
            format_type: The output format type
        """
        if isinstance(format_type, str):
            format_type = OutputFormat(format_type.lower())
        self._output_format = format_type
        return self
    
    def set_output_schema(self, schema: Dict[str, Any]) -> 'InstructionBuilder':
        """
        Set the output schema for structured outputs.
        
        Args:
            schema: JSON schema for the output
        """
        self._output_schema = schema
        return self
    
    def add_constraint(self, constraint: str) -> 'InstructionBuilder':
        """
        Add a constraint/rule.
        
        Args:
            constraint: Constraint description
        """
        self._constraints.append(constraint)
        return self
    
    def add_constraints(self, constraints: List[str]) -> 'InstructionBuilder':
        """
        Add multiple constraints.
        
        Args:
            constraints: List of constraint descriptions
        """
        self._constraints.extend(constraints)
        return self
    
    def add_example(self, input_text: str, output_text: str, explanation: str = "") -> 'InstructionBuilder':
        """
        Add an example.
        
        Args:
            input_text: Example input
            output_text: Example output
            explanation: Optional explanation
        """
        example = {
            "input": input_text,
            "output": output_text
        }
        if explanation:
            example["explanation"] = explanation
        self._examples.append(example)
        return self
    
    def set_variable(self, name: str, value: Any) -> 'InstructionBuilder':
        """
        Set a variable for template substitution.
        
        Args:
            name: Variable name
            value: Variable value
        """
        self._variables[name] = value
        return self
    
    def set_variables(self, variables: Dict[str, Any]) -> 'InstructionBuilder':
        """
        Set multiple variables.
        
        Args:
            variables: Dictionary of variables
        """
        self._variables.update(variables)
        return self
    
    def extend_from(self, parent: 'InstructionBuilder') -> 'InstructionBuilder':
        """
        Extend instructions from a parent builder (inheritance).
        
        Args:
            parent: Parent instruction builder
        """
        self._parent = parent
        return self
    
    def build(self) -> StructuredInstruction:
        """
        Build the structured instruction.
        
        Returns:
            StructuredInstruction object
        """
        # Start with parent values if inheriting
        base_prompt = ""
        formatting_rules = {}
        constraints = []
        examples = []
        variables = {}
        
        if self._parent:
            parent_instruction = self._parent.build()
            base_prompt = parent_instruction.base_prompt
            formatting_rules = parent_instruction.formatting_rules.copy()
            constraints = parent_instruction.constraints.copy()
            examples = parent_instruction.examples.copy()
            variables = parent_instruction.variables.copy()
        
        # Build the full prompt
        prompt_parts = []
        
        # Add parent prompt
        if base_prompt:
            prompt_parts.append(base_prompt)
        
        # Add own base prompt
        if self._base_prompt:
            prompt_parts.append(self._base_prompt)
        
        # Add sections
        for section in self._sections:
            prompt_parts.append(f"\n## {section['title']}\n{section['content']}")
        
        # Add examples section if examples exist
        all_examples = examples + self._examples
        if all_examples:
            prompt_parts.append("\n## EXAMPLES")
            for i, ex in enumerate(all_examples, 1):
                prompt_parts.append(f"\nExample {i}:")
                prompt_parts.append(f"Input: {ex['input']}")
                prompt_parts.append(f"Output: {ex['output']}")
                if ex.get('explanation'):
                    prompt_parts.append(f"Explanation: {ex['explanation']}")
        
        # Merge with own values
        formatting_rules.update(self._formatting_rules)
        constraints.extend(self._constraints)
        variables.update(self._variables)
        
        return StructuredInstruction(
            base_prompt="\n".join(prompt_parts),
            formatting_rules=formatting_rules,
            output_format=self._output_format,
            output_schema=self._output_schema,
            constraints=constraints,
            examples=all_examples,
            variables=variables
        )
    
    def render(self, context: Dict[str, Any] = None) -> str:
        """
        Build and render the instruction with context.
        
        Args:
            context: Context variables for rendering
            
        Returns:
            Rendered instruction string
        """
        instruction = self.build()
        return instruction.render(context)
    
    @classmethod
    def from_template(cls, template_str: str, variables: Dict[str, Any] = None) -> 'InstructionBuilder':
        """
        Create an instruction builder from a template string.
        
        Args:
            template_str: Template string with {variable} placeholders
            variables: Variables to substitute
            
        Returns:
            InstructionBuilder instance
        """
        builder = cls(template_str)
        if variables:
            builder.set_variables(variables)
        return builder
    
    @classmethod
    def create_conversational(cls, persona: str, capabilities: List[str] = None) -> 'InstructionBuilder':
        """
        Create a conversational agent instruction builder.
        
        Args:
            persona: Agent persona description
            capabilities: List of agent capabilities
            
        Returns:
            InstructionBuilder configured for conversational agents
        """
        builder = cls()
        builder.set_base_prompt(f"You are {persona}.")
        
        if capabilities:
            builder.add_section("CAPABILITIES", "\n".join(f"- {cap}" for cap in capabilities))
        
        builder.add_section("CONVERSATION GUIDELINES", """
- Engage in natural, helpful conversation
- Ask clarifying questions when the user's intent is unclear
- Provide concise but complete answers
- Remember context from earlier in the conversation
- Be proactive in suggesting relevant follow-up actions""")
        
        builder.add_constraint("Always maintain a helpful and professional tone")
        builder.add_constraint("If you cannot complete a task, explain why and suggest alternatives")
        
        return builder
    
    @classmethod
    def create_task_oriented(cls, task_description: str, tools: List[str] = None) -> 'InstructionBuilder':
        """
        Create a task-oriented agent instruction builder.
        
        Args:
            task_description: Description of the task
            tools: List of available tools
            
        Returns:
            InstructionBuilder configured for task-oriented agents
        """
        builder = cls()
        builder.set_base_prompt(f"Your task is to: {task_description}")
        
        if tools:
            builder.add_section("AVAILABLE TOOLS", "\n".join(f"- {tool}" for tool in tools))
        
        builder.add_section("TASK EXECUTION", """
1. Analyze the request carefully
2. Break down complex tasks into subtasks
3. Use appropriate tools to complete each subtask
4. Verify the results before reporting completion
5. Report any issues or blockers encountered""")
        
        builder.add_constraint("Complete the task efficiently with minimal tool calls")
        builder.add_constraint("Validate outputs before marking the task as complete")
        
        return builder
    
    @classmethod
    def create_autonomous(cls, goal: str, escalation_rules: List[str] = None) -> 'InstructionBuilder':
        """
        Create an autonomous agent instruction builder.
        
        Args:
            goal: The agent's primary goal
            escalation_rules: Rules for when to escalate
            
        Returns:
            InstructionBuilder configured for autonomous agents
        """
        builder = cls()
        builder.set_base_prompt(f"""You are an autonomous agent with the goal: {goal}

You operate independently, making decisions and executing tasks without constant user input.
You should plan, execute, learn from results, and adapt your approach as needed.""")
        
        builder.add_section("AUTONOMOUS OPERATION", """
1. PLAN: Analyze the goal and create a step-by-step plan
2. EXECUTE: Execute each step, monitoring for issues
3. ADAPT: If a step fails, analyze why and try alternative approaches
4. LEARN: Record successful patterns for future use
5. ESCALATE: When stuck or facing critical decisions, escalate appropriately""")
        
        if escalation_rules:
            builder.add_section("ESCALATION RULES", "\n".join(f"- {rule}" for rule in escalation_rules))
        
        builder.add_constraint("Make autonomous decisions within your defined scope")
        builder.add_constraint("Escalate to human review for decisions outside your authority")
        builder.add_constraint("Always prioritize safety and correctness over speed")
        
        return builder

