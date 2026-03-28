"""
mcp_client.py — Genuine Python caller for AttractorFlow MCP tools.

Maintains a persistent stdio session to the AttractorFlow MCP server so that
the server's in-memory PhaseSpaceMonitor is preserved across all tool calls.

Usage:
    import asyncio
    from evolve_sys.mcp_client import AttractorFlowClient

    async def main():
        async with AttractorFlowClient() as af:
            await af.record_state("cycle 1 starting", goal_text="improve quality")
            result = await af.get_regime()
            print(result["regime"])   # real value from server

    asyncio.run(main())
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

_SERVER = Path.home() / ".claude/plugins/cache/attractor-flow/attractorflow/mcp-server/server.py"


class AttractorFlowClient:
    """
    Persistent async MCP session to the AttractorFlow server.

    Open once per run with `async with AttractorFlowClient() as af:`.
    Keeps the server subprocess alive so the PhaseSpaceMonitor buffer
    accumulates across all tool calls.
    """

    def __init__(self) -> None:
        self._session: Any = None
        self._stack: Any = None

    async def __aenter__(self) -> "AttractorFlowClient":
        from contextlib import AsyncExitStack
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        self._stack = AsyncExitStack()
        params = StdioServerParameters(
            command="uv",
            args=["run", "--no-project", str(_SERVER)],
        )
        read, write = await self._stack.enter_async_context(stdio_client(params))
        self._session = await self._stack.enter_async_context(ClientSession(read, write))
        await self._session.initialize()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._stack.aclose()

    async def call(self, tool: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        """Call a named MCP tool and return the parsed JSON response."""
        result = await self._session.call_tool(tool, args or {})
        return json.loads(result.content[0].text)  # type: ignore[index]

    # ── Convenience wrappers for the 8 AttractorFlow tools ───────────────────

    async def record_state(self, state_text: str, goal_text: str = "") -> dict[str, Any]:
        """Record current agent state in embedding space."""
        return await self.call(
            "attractorflow_record_state",
            {"state_text": state_text, "goal_text": goal_text},
        )

    async def get_regime(self) -> dict[str, Any]:
        """Classify current trajectory regime (CONVERGING/EXPLORING/STUCK/etc.)."""
        return await self.call("attractorflow_get_regime")

    async def get_lyapunov(self) -> dict[str, Any]:
        """Get full FTLE result including SVD singular values and isotropy ratio."""
        return await self.call("attractorflow_get_lyapunov")

    async def get_trajectory(self) -> dict[str, Any]:
        """Get recent trajectory statistics."""
        return await self.call("attractorflow_get_trajectory")

    async def get_basin_depth(self) -> dict[str, Any]:
        """Estimate depth within current attractor basin."""
        return await self.call("attractorflow_get_basin_depth")

    async def detect_bifurcation(self) -> dict[str, Any]:
        """Detect PITCHFORK, HOPF, or SADDLE_NODE bifurcation events."""
        return await self.call("attractorflow_detect_bifurcation")

    async def inject_perturbation(self, magnitude: float = 0.5) -> dict[str, Any]:
        """Generate a perturbation hint to escape STUCK/OSCILLATING/DIVERGING."""
        return await self.call(
            "attractorflow_inject_perturbation",
            {"magnitude": magnitude},
        )

    async def checkpoint(self) -> dict[str, Any]:
        """Save current trajectory as a stable reference checkpoint."""
        return await self.call("attractorflow_checkpoint")
