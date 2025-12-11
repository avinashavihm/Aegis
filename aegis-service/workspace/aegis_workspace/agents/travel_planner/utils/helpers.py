import uuid

def generate_agent_name(base_name: str) -> str:
    """
    Generates a unique agent name.

    Args:
        base_name: The base name for the agent.

    Returns:
        A unique agent name.
    """
    unique_id = str(uuid.uuid4())[:8]  # Use the first 8 characters of a UUID
    return f"{base_name}-{unique_id}"