"""
Time model for the ATC MCP server.

Epoch: t=0 is the moment a schedule is generated. The scheduler never reads wall-clock time.
Granularity: integer seconds. All durations, buffers, and placements are non-negative integers
expressed as (start_sec, end_sec) pairs.

Invariant: every time value in domain/ and scheduler/ must be a non-negative int.
Banned in domain/ and scheduler/: time.time(), datetime.now(), datetime.utcnow(), random.
"""

Seconds = int
