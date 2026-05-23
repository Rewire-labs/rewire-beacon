"""Background workers: Kafka consumers, retry loops, cleanup jobs.

Each worker is a standalone CLI runnable (uvicorn-style):
  python -m beacon.workers.email_sender
"""
