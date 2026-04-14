"""
LLMs Katmanı — BaseModel ve SubModel'leri dışa aktarır.
Boot sırasında tüm SubModel'leri otomatik olarak yükler ve registry'ye kaydeder.
"""

from .BaseModel import BaseModel
from .SubModels import SubModel, get_submodel, list_submodels, register_submodel, get_all_submodels

# Gecici sade mod: sadece browser_agent import edilerek auto-register olur.
from .SubModels import browser_agent  # noqa: F401

__all__ = [
    "BaseModel",
    "SubModel",
    "get_submodel",
    "get_all_submodels",
    "list_submodels",
    "register_submodel",
]
