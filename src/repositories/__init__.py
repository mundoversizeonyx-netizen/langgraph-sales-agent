"""Repository exports."""
from src.repositories.base import ProductRepository
from src.repositories.json_repo import get_repository

__all__ = ["ProductRepository", "get_repository"]
