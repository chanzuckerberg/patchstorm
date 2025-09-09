"""
Exceptions for PatchStorm.
"""

class PatchStormParserError(Exception):
    """
    Exception raised for parsing errors in PatchStorm.
    
    This exception is meant to replace parser.error() calls in order to make
    the code more testable. When the script is run directly, we can catch this
    exception and pass it to parser.error(). When imported as a module for testing,
    we can catch and assert against this exception.
    
    Attributes:
        message (str): The error message.
    """
    
    def __init__(self, message):
        """
        Initialize with an error message.
        
        Args:
            message (str): The error message.
        """
        self.message = message
        super().__init__(message)