"""
Configuration management for Aegis
"""

import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()


def str_to_bool(value) -> bool:
    """Convert string to bool"""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    true_values = {'true', 'yes', '1', 'on', 't', 'y'}
    false_values = {'false', 'no', '0', 'off', 'f', 'n'}
    value = str(value).lower().strip()
    if value in true_values:
        return True
    if value in false_values:
        return False
    return False


# Workspace configuration
WORKSPACE_DIR = os.getenv('WORKSPACE_DIR', 'workspace')
LOCAL_ROOT = os.getenv('LOCAL_ROOT', os.getcwd())

# Debug and logging
DEBUG = str_to_bool(os.getenv('DEBUG', False))
LOG_PATH = os.getenv('LOG_PATH', None)

# Model configuration
COMPLETION_MODEL = os.getenv('COMPLETION_MODEL', 'gemini/gemini-2.0-flash')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small')

# Function calling configuration
FN_CALL = str_to_bool(os.getenv('FN_CALL', True))
API_BASE_URL = os.getenv('API_BASE_URL', None)

# Models that don't support function calling
NOT_SUPPORT_FN_CALL = ["o1-mini", "deepseek-reasoner", "deepseek-r1", "llama", "grok-2"]
NOT_USE_FN_CALL = ["deepseek-chat"] + NOT_SUPPORT_FN_CALL

# Models that don't support sender field
NOT_SUPPORT_SENDER = ["mistral", "groq"]

# Models that require ADD_USER
MUST_ADD_USER = ["deepseek-reasoner", "o1-mini", "deepseek-r1"]
ADD_USER = str_to_bool(os.getenv('ADD_USER', None))

# Auto-detect function calling support
if FN_CALL is None:
    FN_CALL = True
    for model in NOT_USE_FN_CALL:
        if model in COMPLETION_MODEL:
            FN_CALL = False
            break

# Auto-detect ADD_USER requirement
if ADD_USER is None:
    ADD_USER = False
    for model in MUST_ADD_USER:
        if model in COMPLETION_MODEL:
            ADD_USER = True
            break

NON_FN_CALL = False
for model in NOT_SUPPORT_FN_CALL:
    if model in COMPLETION_MODEL:
        NON_FN_CALL = True
        break

