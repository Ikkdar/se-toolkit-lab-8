# Observability Skill

You have access to observability tools for querying VictoriaLogs and VictoriaTraces.

## Available Tools

### Log tools (VictoriaLogs)
- `logs_search` — Search logs using LogsQL query
  - Use for finding errors, debugging issues
  - Example query: `_stream:{service="backend"} AND level:error`
  - Example query: `event:"request_completed" AND status:500`

- `logs_error_count` — Count errors per service over a time window
  - Use for monitoring service health
  - Default service: "backend"
  - Default time window: 1 hour

### Trace tools (VictoriaTraces)
- `traces_list` — List recent traces for a service
  - Use for understanding request flow and latency
  - Default service: "backend"

- `traces_get` — Fetch a specific trace by ID
  - Use for detailed debugging of a specific request
  - You can find trace IDs in log entries (trace_id field)

### LMS tools
- `lms_health` — Check if LMS backend is healthy

## Guidelines

### When the user asks "What went wrong?" or "Check system health":

1. **First, check LMS health** — call `lms_health` to see if backend is up

2. **Search recent error logs** — call `logs_error_count` with hours=1
   - If errors found, call `logs_search` with query for recent errors
   - Look for trace_id in error log entries

3. **If you find a trace_id**, call `traces_get` to see the full trace
   - Identify which span failed
   - Note the error message and service

4. **Summarize findings concisely:**
   - Start with the bottom line: "The backend is down" or "Database connection failed"
   - List evidence from logs (error messages, timestamps)
   - List evidence from traces (failed spans, services involved)
   - Don't dump raw JSON — explain in plain English
   - Offer next steps: "Would you like me to investigate further?"

### When the user asks about errors in a time window:

1. Call `logs_error_count` for the specified time window
2. If errors found, call `logs_search` for details
3. Summarize: count, services affected, error types

### When debugging an issue:

1. Start with `logs_search` using relevant keywords
2. Look for trace_id in error logs
3. Use `traces_get` to see the full request flow
4. Identify which service/span caused the failure
5. Report findings clearly
