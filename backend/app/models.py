from datetime import datetime
from enum import Enum

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class StaffRole(str, Enum):
    ADMIN = 'ADMIN'
    CHEF = 'CHEF'
    WAITRESS = 'WAITRESS'


class CustomerRole(str, Enum):
    CUSTOMER = 'CUSTOMER'


class UserStatus(str, Enum):
    ACTIVE = 'ACTIVE'
    INACTIVE = 'INACTIVE'


class TableStatus(str, Enum):
    ACTIVE = 'ACTIVE'
    INACTIVE = 'INACTIVE'


class TableSessionStatus(str, Enum):
    ACTIVE = 'ACTIVE'
    CLOSED = 'CLOSED'


class FoodType(str, Enum):
    VEG = 'VEG'
    NON_VEG = 'NON_VEG'


class OTPStatus(str, Enum):
    PENDING = 'PENDING'
    VERIFIED = 'VERIFIED'
    EXPIRED = 'EXPIRED'
    LOCKED = 'LOCKED'


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    role: StaffRole
    username: str = Field(index=True, unique=True)
    password_hash: str
    status: UserStatus = Field(default=UserStatus.ACTIVE)
    created_by: int | None = Field(default=None, foreign_key='user.id')
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Customer(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    mobile_number: str = Field(index=True, unique=True)
    is_verified: bool = Field(default=False)
    last_login_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class OTPRequest(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    mobile_number: str = Field(index=True)
    otp_hash: str
    expires_at: datetime
    attempts: int = Field(default=0)
    status: OTPStatus = Field(default=OTPStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RestaurantTable(SQLModel, table=True):
    __tablename__ = 'restaurant_table'

    id: int | None = Field(default=None, primary_key=True)
    table_number: str = Field(index=True, unique=True)
    qr_code_value: str = Field(index=True, unique=True)
    status: TableStatus = Field(default=TableStatus.ACTIVE)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TableSession(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    table_id: int = Field(foreign_key='restaurant_table.id', index=True)
    customer_id: int = Field(foreign_key='customer.id', index=True)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: datetime | None = None
    status: TableSessionStatus = Field(default=TableSessionStatus.ACTIVE)
    assigned_by_role: str = Field(default='SYSTEM')
    assigned_by_id: int | None = None
    offboarded_by: int | None = None


class MenuCategory(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    is_active: bool = Field(default=True)


class MenuItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str
    price: float
    category_id: int | None = Field(default=None, foreign_key='menucategory.id')
    food_type: FoodType
    is_available: bool = Field(default=True, index=True)
    stock_qty: int | None = None
    image_url: str | None = None
    updated_by: int | None = Field(default=None, foreign_key='user.id')
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AuditLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    actor_type: str
    actor_id: int | None = None
    action: str
    entity_type: str
    entity_id: int | None = None
    details: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
