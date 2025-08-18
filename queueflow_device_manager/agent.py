from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPServerParams
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.models.lite_llm import LiteLlm
import logging
from .config import config
from . import prompts

logger = logging.getLogger(__name__)

root_agent = LlmAgent(
    model=LiteLlm(
        model=config.MODEL,
        api_key=config.API_KEY,
        # kwargs={"enable_thinking": False},
    ),
    name=config.name,
    description="A Model Context Protocol (MCP) Orchestrator AI Agent for managing queue flows.",
    instruction=prompts.INSTRUCTION,
    tools=[
        MCPToolset(
            connection_params=StreamableHTTPServerParams(
                url="http://localhost:6969/mcp",
            ),
            tool_filter=[
                "get_queue_policy",
                "get_current_queue_policy",
                "select_queue_policy",
                "get_policy_config",
                "update_policy_config",
                "get_queue_length",
                "start_queue_management",
                "stop_queue_management",
                "get_queue_management_status",
            ],
        ),
        MCPToolset(
            connection_params=StreamableHTTPServerParams(
                url="http://localhost:6970/mcp",
            ),
            tool_filter=[
                "get_devices",
                "power_on_devices",
                "power_off_devices",
            ],
        ),
    ],
)
