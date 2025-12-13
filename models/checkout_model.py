from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from enum import Enum

class DeliveryOption(str, Enum):
    STANDARD = "standard"
    EXPRESS = "express"
    SAME_DAY = "same_day"
    PICKUP = "pickup"

class PaymentMethod(str, Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    CASH_ON_DELIVERY = "cash_on_delivery"
    GCASH = "gcash"
    PAYMAYA = "paymaya"
    BANK_TRANSFER = "bank_transfer"

class ShippingAddressInput(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    phone: str = Field(..., min_length=1, max_length=20)
    address_line1: str = Field(..., min_length=1, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=1, max_length=100)
    postal_code: str = Field(..., min_length=1, max_length=20)
    country: str = Field(default="Philippines", max_length=100)

class CheckoutRequest(BaseModel):
    shipping_address: ShippingAddressInput
    delivery_option: DeliveryOption
    payment_method: PaymentMethod
    customer_notes: Optional[str] = None

class OrderItemResponse(BaseModel):
    product_id: int
    product_name: str
    variant_id: Optional[int]
    variant_name: Optional[str]
    variant_value: Optional[str]
    quantity: int
    price: Decimal
    subtotal: Decimal
    image_url: Optional[str]

class OrderSummaryResponse(BaseModel):
    subtotal: Decimal
    tax: Decimal
    shipping_fee: Decimal
    marketplace_fee: Decimal
    discount: Decimal
    total: Decimal
    items: List[OrderItemResponse]
    item_count: int

class OrderResponse(BaseModel):
    order_id: int
    order_number: str
    status: str
    payment_status: str
    payment_method: str
    subtotal: Decimal
    tax: Decimal
    shipping_fee: Decimal
    marketplace_fee: Decimal
    discount: Decimal
    total: Decimal
    shipping_address: ShippingAddressInput
    delivery_option: str
    estimated_delivery_date: Optional[date]
    customer_notes: Optional[str]
    items: List[OrderItemResponse]
    created_at: datetime
    
    class Config:
        from_attributes = True