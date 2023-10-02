from abc import ABC, abstractmethod
from typing import List, Optional

from openplugin.interfaces.models import (
    LLM,
    Config,
    Message,
    Plugin,
    SelectedApiSignatureResponse,
    ToolSelectorConfig,
)


class OperationSignatureBuilder(ABC):
    """Abstract base class for plugin selectors."""

    def __init__(
        self,
        tool_selector_config: ToolSelectorConfig,
        plugin: Plugin,
        config: Optional[Config],
        llm: Optional[LLM],
    ):
        """
        Initialize the plugin selector.
        Args:
            tool_selector_config (ToolSelectorConfig): Configuration for the tool.
            plugins (List[Plugin]): List of plugins to be used by the plugin selector.
            config (Optional[Config]): Additional configuration for the plugin selector.
            llm (Optional[LLM]): Additional language model for the plugin selector.
        """
        self.tool_selector_config = tool_selector_config
        self.plugin = plugin
        self.config = config
        self.llm = llm

    @abstractmethod
    def run(self, messages: List[Message]) -> SelectedApiSignatureResponse:
        """
        Run the plugin selector on the given list of messages and return a response.
        This method should be implemented by the derived classes.
        Args:
            messages (List[Message]): List of messages to be processed by the selector.
        Returns:
            Response: The response generated by the plugin selector.
        """
        pass
