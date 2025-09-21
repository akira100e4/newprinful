# products/__init__.py
from .tshirt import TShirtProduct
from .hoodie import HoodieProduct

PRODUCT_CLASSES = {
    'tshirt': TShirtProduct,
    'hoodie': HoodieProduct
}

def create_product(product_type: str):
    """Factory per creare istanze di prodotto"""
    if product_type in PRODUCT_CLASSES:
        return PRODUCT_CLASSES[product_type]()
    else:
        raise ValueError(f"Tipo di prodotto non supportato: {product_type}")

__all__ = ['TShirtProduct', 'HoodieProduct', 'create_product', 'PRODUCT_CLASSES']