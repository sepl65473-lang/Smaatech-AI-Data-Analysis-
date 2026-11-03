"""The legacy business-logic API tests predate authentication and test those APIs directly.

The dedicated authentication tests explicitly turn enforcement back on. This setting is
pytest-only; the application defaults to requiring auth unless an operator overrides it.
"""
import os

os.environ.setdefault("AUTH_REQUIRED", "false")
