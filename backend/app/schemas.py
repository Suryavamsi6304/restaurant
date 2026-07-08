from datetime import datetime

from pydantic import BaseModel, Field

from app.models import FoodType, StaffRole, TableSessionStatus, TableStatus, UserStatus


class MessageResponse(BaseModel):
    message: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'
    role: str


class StaffLoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class OTPRequestPayload(BaseModel):
    mobile_number: str = Field(min_length=10, max_length=20)


class OTPVerifyPayload(BaseModel):
    mobile_number: str = Field(min_length=10, max_length=20)
    otp_code: str = Field(min_length=4, max_length=6)
    qr_code_value: str | None = None


class TableResolveResponse(BaseModel):
    id: int
    table_number: str
    status: TableStatus
    qr_code_value: str


class TableAssignmentRequest(BaseModel):
    qr_code_value: str


class UserCreateRequest(BaseModel):
    role: StaffRole
    username: str
    password: str = Field(min_length=8)


class UserUpdateRequest(BaseModel):
    username: str | None = None
    role: StaffRole | None = None


class UserStatusUpdateRequest(BaseModel):
    status: UserStatus


class PasswordResetRequest(BaseModel):
    password: str = Field(min_length=8)


class UserResponse(BaseModel):
    id: int
    username: str
    role: StaffRole
    status: UserStatus
    created_at: datetime


class TableCreateRequest(BaseModel):
    table_number: str


class TableUpdateRequest(BaseModel):
    table_number: str | None = None
    status: TableStatus | None = None


class TableResponse(BaseModel):
    id: int
    table_number: str
    qr_code_value: str
    status: TableStatus


class MenuCategoryResponse(BaseModel):
    id: int
    name: str
    is_active: bool


class MenuItemCreateRequest(BaseModel):
    name: str
    description: str
    price: float = Field(gt=0)
    category_id: int | None = None
    food_type: FoodType
    is_available: bool = True
    stock_qty: int | None = Field(default=None, ge=0)
    image_url: str | None = None


class MenuItemUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = Field(default=None, gt=0)
    category_id: int | None = None
    food_type: FoodType | None = None
    is_available: bool | None = None
    stock_qty: int | None = Field(default=None, ge=0)
    image_url: str | None = None


class MenuAvailabilityRequest(BaseModel):
    is_available: bool
    stock_qty: int | None = Field(default=None, ge=0)


class MenuItemResponse(BaseModel):
    id: int
    name: str
    description: str
    price: float
    category_id: int | None
    category_name: str | None
    food_type: FoodType
    is_available: bool
    stock_qty: int | None
    image_url: str | None
    updated_at: datetime


class WaitressRegisterCustomerRequest(BaseModel):
    table_id: int
    mobile_number: str = Field(min_length=10, max_length=20)
    override_active_session: bool = False


class WaitressOffboardRequest(BaseModel):
    table_session_id: int


class TableSessionResponse(BaseModel):
    id: int
    table_id: int
    table_number: str
    customer_id: int
    customer_mobile_number: str
    started_at: datetime
    ended_at: datetime | None
    status: TableSessionStatus


class AuditLogResponse(BaseModel):
    id: int
    actor_type: str
    actor_id: int | None
    action: str
    entity_type: str
    entity_id: int | None
    details: dict
    created_at: datetime


class OTPRequestResponse(BaseModel):
    message: str
    expires_in_seconds: int
    otp_code: str | None = None
