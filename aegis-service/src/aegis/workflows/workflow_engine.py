"""
Simple workflow engine for sequential and parallel execution
"""

import asyncio
from typing import List, Callable, Dict, Any, Optional
from aegis.logger import LoggerManager

logger = LoggerManager.get_logger()


class WorkflowEngine:
    """Simple workflow orchestration engine"""
    
    def __init__(self):
        self.logger = logger
    
    async def run_sequential(self, steps: List[Callable], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run workflow steps sequentially.
        
        Args:
            steps: List of callable functions to execute
            context: Context dictionary passed to each step
            
        Returns:
            Dictionary with results from all steps
        """
        if context is None:
            context = {}
        
        results = {}
        for i, step in enumerate(steps):
            try:
                self.logger.info(f"Executing step {i+1}/{len(steps)}", title="Workflow")
                if asyncio.iscoroutinefunction(step):
                    result = await step(context)
                else:
                    result = step(context)
                results[f"step_{i+1}"] = result
                context.update({"last_result": result})
            except Exception as e:
                self.logger.error(f"Error in step {i+1}: {str(e)}", title="Workflow Error")
                results[f"step_{i+1}"] = {"error": str(e)}
                break
        
        return results
    
    async def run_parallel(self, steps: List[Callable], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run workflow steps in parallel.
        
        Args:
            steps: List of callable functions to execute
            context: Context dictionary passed to each step
            
        Returns:
            Dictionary with results from all steps
        """
        if context is None:
            context = {}
        
        async def run_step(step: Callable, step_id: int):
            try:
                if asyncio.iscoroutinefunction(step):
                    result = await step(context)
                else:
                    result = step(context)
                return (step_id, {"success": True, "result": result})
            except Exception as e:
                return (step_id, {"success": False, "error": str(e)})
        
        tasks = [run_step(step, i) for i, step in enumerate(steps)]
        results_list = await asyncio.gather(*tasks)
        
        results = {}
        for step_id, result in results_list:
            results[f"step_{step_id+1}"] = result
        
        return results
    
    def run_sequential_sync(self, steps: List[Callable], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Synchronous version of run_sequential"""
        return asyncio.run(self.run_sequential(steps, context))
    
    def run_parallel_sync(self, steps: List[Callable], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Synchronous version of run_parallel"""
        return asyncio.run(self.run_parallel(steps, context))

