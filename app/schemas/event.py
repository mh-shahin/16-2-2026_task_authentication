from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from fastapi import UploadFile


class EventImageOut(BaseModel):
    image_url: str
    cloudinary_public_id: Optional[str] = None


class EventCreate(BaseModel):
    title: str
    description: str
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    ticket_price: float
    ticket_limit: int
    event_date: datetime
    images: List[UploadFile] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str):
        if len(v.strip().split()) < 1:
            raise ValueError("Event title must be at least 1 word")
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str):
        if len(v.strip().split()) < 10:
            raise ValueError("Event description must be at least 10 words")
        return v.strip()

    @field_validator("ticket_price")
    @classmethod
    def validate_price(cls, v: float):
        if v < 0:
            raise ValueError("Ticket price must be non-negative")
        return v

    @field_validator("ticket_limit")
    @classmethod
    def validate_limit(cls, v: int):
        if v <= 0:
            raise ValueError("Ticket limit must be a positive integer")
        return v

    @field_validator("images")
    @classmethod
    def validate_images(cls, v: List[UploadFile]):
        if len(v) > 5:
            raise ValueError("You can upload a maximum of 5 images per event")
        return v


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    ticket_limit: Optional[int] = None
    event_date: Optional[datetime] = None
    images: List[UploadFile] = Field(default_factory=list)


    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]):
        if v is not None and len(v.strip().split()) < 1:
            raise ValueError("Event title must be at least 1 word")
        return v.strip() if v else v



    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]):
        if v is not None and len(v.strip().split()) < 10:
            raise ValueError("Event description must be at least 10 words")
        return v.strip() if v else v



    @field_validator("ticket_limit")
    @classmethod
    def validate_limit(cls, v: Optional[int]):
        if v is not None and v <= 0:
            raise ValueError("Ticket limit must be a positive integer")
        return v





class EventOut(BaseModel):
    id: int
    manager_id: int
    manager_username: str
    title: str
    description: str
    location: str
    latitude: Optional[float]
    longitude: Optional[float]
    ticket_price: float
    ticket_limit: int
    tickets_sold: int
    tickets_available: int
    event_date: datetime
    images: List[EventImageOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    is_active: bool
    