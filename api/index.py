"""
DEPRECATED for production conversion workloads.

This Vercel Python serverless entry is not suitable for multi-minute PDF/Excel
pipelines (timeouts, ephemeral disk, native lib limits).

Production architecture:
  - Frontend: Vercel (Next.js under /frontend)
  - Backend:  Render (uvicorn backend.main:app — see render.yaml)

Kept only so accidental imports do not break; do not route conversion traffic here.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Intentionally do not export a long-running conversion ASGI app for Vercel.
# Render hosts backend.main:app instead.
from backend.main import app  # noqa: F401

__all__ = ["app"]
