"""Agent domain exceptions."""


class AgentError(Exception):
    """Base agent error."""


class EmptyObjectiveError(AgentError):
    """Raised when an investigation objective is empty."""


class AgentRunNotFoundError(AgentError):
    """Raised when an agent run is missing or not accessible."""


class UnknownToolError(AgentError):
    """Raised when the orchestrator requests a tool outside the registry."""

    def __init__(self, tool_name: str) -> None:
        super().__init__(f"Unknown tool: {tool_name}")
        self.tool_name = tool_name


class AgentOrchestrationError(AgentError):
    """Raised when the agent loop cannot continue."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class AgentCompletionError(AgentError):
    """Raised when agent LLM completion fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
