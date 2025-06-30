"""
CitizenAI Government Services Store Package

This package provides classes for managing government services specifications
in an in-memory store with search functionality.
"""

from .government_services_store import GovernmentService, GovernmentServicesStore

__version__ = "1.0.0"
__all__ = ["GovernmentService", "GovernmentServicesStore"]
