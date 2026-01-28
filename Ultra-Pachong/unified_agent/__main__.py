"""统一入口 - 启动Agent"""
import asyncio
from .api.orchestrator import AgentOrchestrator


def main():
    """主入口"""
    agent = AgentOrchestrator()
    print("Unified Agent Started")
    print(f"Available tools: {[t['name'] for t in agent.mcp.registry.list_tools()]}")
    # TODO: 启动HTTP服务或CLI交互


if __name__ == "__main__":
    main()
