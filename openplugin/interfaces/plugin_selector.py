from typing import List, Optional
from abc import ABC, abstractmethod
from openplugin import Message, LLM, Plugin, ToolSelectorConfig, Config, SelectedPluginsResponse


class PluginSelector(ABC):
    """Abstract base class for plugin selectors."""

    def __init__(
            self,
            tool_selector_config: ToolSelectorConfig,
            plugins: List[Plugin],
            config: Optional[Config],
            llm: Optional[LLM]
    ):
        """
        Initialize the plugin selector.
        Args:
            tool_selector_config (ToolSelectorConfig): Configuration for the tool selector.
            plugins (List[Plugin]): List of plugins to be used by the plugin selector.
            config (Optional[Config]): Additional configuration for the plugin selector.
            llm (Optional[LLM]): Additional language model for the plugin selector.
        """
        self.tool_selector_config = tool_selector_config
        self.plugins = plugins
        self.config = config
        self.llm = llm

    def get_plugin_by_name(self, name: str):
        for plugin in self.plugins:
            if plugin.name == name:
                return plugin
        return None

    @abstractmethod
    def run(
            self,
            messages: List[Message]
    ) -> SelectedPluginsResponse:
        """
        Run the plugin selector on the given list of messages and return a response.
        This method should be implemented by the derived classes.
        Args:
            messages (List[Message]): List of messages to be processed by the plugin selector.
        Returns:
            Response: The response generated by the plugin selector.
        """
        pass
