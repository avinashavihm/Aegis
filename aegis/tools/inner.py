"""
Internal tools for case resolution
"""

from aegis.types import Result


def case_resolved(result: str, context_variables: dict = None) -> str:
    """
    Use this tool to indicate that the case is resolved. You can use this tool only after you truly resolve the case with existing tools and created new tools.
    Please encapsulate your final answer (answer ONLY) within <solution> and </solution>.
    
    Args:
        result: The final result of the case resolution following the instructions.
        
    Example: case_resolved(`The answer to the question is <solution> 42 </solution>`)
    """
    return f"Case resolved. No further actions are needed. The result of the case resolution is: {result}"


def case_not_resolved(failure_reason: str, take_away_message: str, context_variables: dict = None) -> str:
    """
    Use this tool to indicate that the case is not resolved when all agents have tried their best.
    [IMPORTANT] Please do not use this function unless all of you have tried your best.
    You should give the failure reason to tell the user why the case is not resolved, and give the take away message to tell which information you gain from creating new tools.
    
    Args:
        failure_reason: The reason why the case is not resolved.
        take_away_message: The message to take away from the case.
    """
    return f"Case not resolved. The reason is: {failure_reason}. But though creating new tools, I gain some information: {take_away_message}"

