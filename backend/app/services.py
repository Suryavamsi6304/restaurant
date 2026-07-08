from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models import (
    AuditLog,
    Customer,
    FoodType,
    MenuCategory,
    MenuItem,
    OTPRequest,
    OTPStatus,
    RestaurantTable,
    TableSession,
    TableSessionStatus,
    TableStatus,
    User,
    UserStatus,
)


def generate_table_qr(table_number: str) -> str:
    return f'TABLE::{table_number}::{uuid4().hex[:10]}'


def record_audit(
    session: Session,
    actor_type: str,
    actor_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | None,
    details: dict | None = None,
) -> None:
    session.add(
        AuditLog(
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
        )
    )


def ensure_staff_user(user: User | None) -> User:
    if user is None or user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid staff credentials.')
    return user


def ensure_table_available(session: Session, table: RestaurantTable, allow_override: bool = False) -> None:
    if table.status != TableStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Table is inactive.')
    active_session = session.exec(
        select(TableSession).where(
            TableSession.table_id == table.id,
            TableSession.status == TableSessionStatus.ACTIVE,
        )
    ).first()
    if active_session and not allow_override:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Table is already occupied.')
    if active_session and allow_override:
        active_session.status = TableSessionStatus.CLOSED
        active_session.ended_at = datetime.utcnow()


def get_or_create_customer(session: Session, mobile_number: str) -> Customer:
    customer = session.exec(select(Customer).where(Customer.mobile_number == mobile_number)).first()
    if customer:
        return customer
    customer = Customer(mobile_number=mobile_number)
    session.add(customer)
    session.flush()
    return customer


def build_menu_item_response(item: MenuItem, category_map: dict[int, MenuCategory]) -> dict:
    category = category_map.get(item.category_id) if item.category_id else None
    return {
        'id': item.id,
        'name': item.name,
        'description': item.description,
        'price': item.price,
        'category_id': item.category_id,
        'category_name': category.name if category else None,
        'food_type': item.food_type,
        'is_available': item.is_available,
        'stock_qty': item.stock_qty,
        'image_url': item.image_url,
        'updated_at': item.updated_at,
    }


def fetch_category_map(session: Session) -> dict[int, MenuCategory]:
    categories = session.exec(select(MenuCategory)).all()
    return {category.id: category for category in categories}


def seed_defaults(session: Session) -> None:
    existing_categories = session.exec(select(MenuCategory)).all()
    if not existing_categories:
        session.add_all(
            [
                MenuCategory(name='Starters'),
                MenuCategory(name='Main Course'),
                MenuCategory(name='Beverages'),
                MenuCategory(name='Desserts'),
            ]
        )
    session.commit()
