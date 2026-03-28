"""Observability MCP tools for querying VictoriaLogs and VictoriaTraces."""

import httpx
import os
from typing import Any

# VictoriaLogs API
VICTORIALOGS_URL = os.environ.get("VICTORIALOGS_URL", "http://victorialogs:9428")

# VictoriaTraces API (Jaeger-compatible)
VICTORIATRACES_URL = os.environ.get("VICTORIATRACES_URL", "http://victoriatraces:10428")


async def logs_search(query: str, limit: int = 100) -> list[dict[str, Any]]:
    """Search VictoriaLogs using LogsQL query.
    
    Args:
        query: LogsQL query string (e.g., '_stream:{service="backend"} AND level:error')
        limit: Maximum number of log entries to return
    
    Returns:
        List of log entries
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{VICTORIALOGS_URL}/select/logsql/query",
            params={"query": query, "limit": limit},
            timeout=30.0
        )
        resp.raise_for_status()
        return resp.json()


async def logs_error_count(service: str = "backend", hours: int = 1) -> dict[str, Any]:
    """Count errors per service over a time window.
    
    Args:
        service: Service name to filter
        hours: Time window in hours
    
    Returns:
        Dictionary with error count
    """
    query = f'_stream:{{service="{service}"}} AND (level:error OR level:ERROR)'
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{VICTORIALOGS_URL}/select/logsql/query",
            params={"query": query, "limit": 1000},
            timeout=30.0
        )
        resp.raise_for_status()
        logs = resp.json()
        return {"service": service, "error_count": len(logs), "time_window_hours": hours}


async def traces_list(service: str = "backend", limit: int = 20) -> list[dict[str, Any]]:
    """List recent traces for a service.
    
    Args:
        service: Service name to filter
        limit: Maximum number of traces to return
    
    Returns:
        List of trace summaries
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{VICTORIATRACES_URL}/jaeger/api/services/{service}/traces",
            params={"limit": limit},
            timeout=30.0
        )
        resp.raise_for_status()
        return resp.json().get("data", [])


async def traces_get(trace_id: str) -> dict[str, Any]:
    """Fetch a specific trace by ID.
    
    Args:
        trace_id: The trace ID to fetch
    
    Returns:
        Full trace with spans
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{VICTORIATRACES_URL}/jaeger/api/traces/{trace_id}",
            timeout=30.0
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        return data[0] if data else {}
