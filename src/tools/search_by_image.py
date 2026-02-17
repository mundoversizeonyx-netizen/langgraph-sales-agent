"""Tool: find products similar to a described image."""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from src.models.catalog import get_catalog


@tool
def search_by_image(image_description: str, config: RunnableConfig) -> str:
    """Find products similar to what's described in a customer's photo.

    Use this AFTER analyzing a customer's image. Pass the description
    of what you see in the image to find matching products.

    Args:
        image_description: Text description of the image content
                           (e.g. "red roses in a glass vase" or "silver laptop").
    """
    tenant_id = config["configurable"]["tenant_id"]
    catalog = get_catalog(tenant_id)
    results = catalog.find_similar(image_description)

    if not results:
        return "No similar products found. I can show you our full catalog instead."

    lines = ["Here are similar products from our catalog:\n"]
    for p in results:
        lines.append(p.to_display())
        lines.append("")
    return "\n".join(lines)
