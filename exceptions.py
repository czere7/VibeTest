"""
Custom exceptions for the test generation workflow.
"""


class ContextWindowOverflowError(Exception):
    """
    Raised when the prompt is too large to fit in the model's context window.
    
    This exception indicates that the request should be skipped and the workflow
    should advance to the next class.
    """
    
    def __init__(self, message: str, node_name: str = None, class_info: str = None):
        """
        Initialize the ContextWindowOverflowError.
        
        Args:
            message: Error message from the API
            node_name: Name of the node where the error occurred
            class_info: Information about the class being processed
        """
        super().__init__(message)
        self.node_name = node_name
        self.class_info = class_info
        self.original_message = message
