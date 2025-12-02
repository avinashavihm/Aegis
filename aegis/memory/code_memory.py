"""
Code context memory for tracking code execution
"""

from typing import Dict, List, Optional
from datetime import datetime
import re


class CodeMemory:
    """Memory system for tracking code execution context"""
    
    def __init__(self, max_context: int = 50):
        self.max_context = max_context
        self.code_snippets: List[Dict] = []
        self.file_contexts: Dict[str, List[str]] = {}
    
    def record_code(self, code: str, result: str, file_path: Optional[str] = None, success: bool = True):
        """Record code execution"""
        record = {
            "code": code[:500] if len(code) > 500 else code,  # Truncate long code
            "result": result[:1000] if len(result) > 1000 else result,
            "file_path": file_path,
            "success": success,
            "timestamp": datetime.now().isoformat()
        }
        
        self.code_snippets.append(record)
        if len(self.code_snippets) > self.max_context:
            self.code_snippets.pop(0)
        
        if file_path:
            if file_path not in self.file_contexts:
                self.file_contexts[file_path] = []
            self.file_contexts[file_path].append(code)
            if len(self.file_contexts[file_path]) > 10:
                self.file_contexts[file_path].pop(0)
    
    def get_recent_code(self, limit: int = 5) -> List[Dict]:
        """Get recent code executions"""
        return self.code_snippets[-limit:]
    
    def get_file_context(self, file_path: str) -> List[str]:
        """Get code context for a specific file"""
        return self.file_contexts.get(file_path, [])
    
    def search_code(self, pattern: str) -> List[Dict]:
        """Search code snippets by pattern"""
        results = []
        for snippet in self.code_snippets:
            if re.search(pattern, snippet["code"], re.IGNORECASE):
                results.append(snippet)
        return results
    
    def clear(self):
        """Clear all memory"""
        self.code_snippets = []
        self.file_contexts = {}


# Global code memory instance
code_memory = CodeMemory()

