# models.py - 统一数据结构
from dataclasses import dataclass
from typing import Optional


@dataclass
class Item:
    id: int
    name: str
    category: str
    owner: str
    purchase_price: Optional[float]
    remark: str
    photo: str
    access_count: int
    last_accessed_at: Optional[str]
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: dict) -> "Item":
        return cls(**{k: row[k] for k in cls.__annotations__})


@dataclass
class ItemLocation:
    id: int
    item_id: int
    location: str
    quantity: int
    reason: Optional[str]
    location_status: str
    purchase_date: Optional[str]
    expiration_date: Optional[str]
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: dict) -> "ItemLocation":
        return cls(**{k: row[k] for k in cls.__annotations__})


@dataclass
class Tag:
    id: int
    item_id: int
    tag: str

    @classmethod
    def from_row(cls, row: dict) -> "Tag":
        return cls(**{k: row[k] for k in cls.__annotations__})
