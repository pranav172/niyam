"""NIYAM Agent-Readable Product Catalog
Exposes machine-checkable policy tags (booleans/enums) and agent-tailored descriptions.
"""
from typing import List, Dict, Any, Optional


CATALOG_PRODUCTS: List[Dict[str, Any]] = [
    {
        "id": "prod_toy_teddy",
        "title": "Wooden Handcrafted Teddy Bear",
        "price": 450.0,
        "category": "toys",
        "policy_tags": {
            "returnable": True,
            "perishable": False,
            "cod_allowed": True,
            "age_group": "3+"
        },
        "agent_description": "Eco-friendly wooden handcrafted teddy bear, 10 inch, non-toxic colors, 7-day returnable window.",
        "in_stock": True,
        "merchant_id": "merch_verified_toys"
    },
    {
        "id": "prod_toy_lego",
        "title": "Robotics Building Blocks Set",
        "price": 1150.0,
        "category": "toys",
        "policy_tags": {
            "returnable": True,
            "perishable": False,
            "cod_allowed": True,
            "age_group": "8+"
        },
        "agent_description": "250-piece motorized robotics kit for STEM learning, returnable within 10 days.",
        "in_stock": True,
        "merchant_id": "merch_verified_toys"
    },
    {
        "id": "prod_toy_custom_doll",
        "title": "Custom Engraved Name Doll",
        "price": 600.0,
        "category": "toys",
        "policy_tags": {
            "returnable": False,  # Non-returnable!
            "perishable": False,
            "cod_allowed": False,
            "age_group": "3+"
        },
        "agent_description": "Personalized wooden doll with engraved name. Custom made: non-returnable and no COD.",
        "in_stock": True,
        "merchant_id": "merch_verified_toys"
    },
    {
        "id": "prod_phone_flagship",
        "title": "RazorUltra Flagship 5G (256GB)",
        "price": 79999.0,
        "category": "electronics",
        "policy_tags": {
            "returnable": True,
            "perishable": False,
            "cod_allowed": False,
            "warranty_years": 2
        },
        "agent_description": "Flagship 5G smartphone with 200MP camera, 120Hz OLED display, high-value asset.",
        "in_stock": True,
        "merchant_id": "merch_electronic_hub"
    },
    {
        "id": "prod_wireless_earbuds",
        "title": "True Wireless Noise-Cancelling Earbuds",
        "price": 899.0,
        "category": "electronics",
        "policy_tags": {
            "returnable": True,
            "perishable": False,
            "cod_allowed": True
        },
        "agent_description": "Compact wireless earbuds with active noise cancellation and 24h battery life.",
        "in_stock": True,
        "merchant_id": "merch_electronic_hub"
    },
    {
        "id": "prod_organic_honey",
        "title": "Raw Organic Forest Honey (500g)",
        "price": 380.0,
        "category": "groceries",
        "policy_tags": {
            "returnable": False,
            "perishable": True,
            "cod_allowed": True
        },
        "agent_description": "100% pure raw unprocessed forest honey. Perishable grocery item, non-returnable.",
        "in_stock": True,
        "merchant_id": "merch_organic_foods"
    },
    {
        "id": "prod_kids_encyclopedia",
        "title": "Illustrated Science & Space Encyclopedia",
        "price": 420.0,
        "category": "books",
        "policy_tags": {
            "returnable": True,
            "perishable": False,
            "cod_allowed": True
        },
        "agent_description": "Hardcover illustrated encyclopedia for kids and students, 14-day returnable.",
        "in_stock": True,
        "merchant_id": "merch_book_store"
    }
]


def get_agent_catalog(category: Optional[str] = None) -> Dict[str, Any]:
    """Returns agent-readable catalog with policy specifications."""
    products = CATALOG_PRODUCTS
    if category:
        products = [p for p in products if p["category"].lower() == category.lower()]
    
    return {
        "catalog_version": "2026.09-v1",
        "currency": "INR",
        "total_items": len(products),
        "products": products,
        "merchant_policies": {
            "standard_return_window_days": 7,
            "supported_rails": ["upi", "cards", "netbanking", "cod"]
        }
    }
