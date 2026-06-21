"""Stream Production Status API integration.

Polls the FSL stream-production tool's read-only status feed, coalesces bursts
of events into a single summarized Mathison statement (anti-spam), and feeds
production context (series score, scene, GG, intros) that the SC2 client cannot
see on its own.
"""
