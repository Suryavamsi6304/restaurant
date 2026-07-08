from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.security import Principal, get_current_principal, require_roles
from app.models import Customer, FoodType, MenuCategory, MenuItem, RestaurantTable, TableSession, TableSessionStatus, TableStatus
from app.schemas import MenuCategoryResponse, MenuItemResponse, TableAssignmentRequest, TableResolveResponse, TableSessionResponse
from app.services import build_menu_item_response, ensure_table_available, fetch_category_map, record_audit

router = APIRouter(prefix='/customer', tags=['customer'])


def get_customer(principal: Principal, session: Session) -> Customer:
    if principal.role != 'CUSTOMER' or principal.customer_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Customer token required.')
    customer = session.get(Customer, principal.customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Customer not found.')
    return customer


@router.get('/table/resolve', response_model=TableResolveResponse)
def resolve_table(qr: str = Query(...), session: Session = Depends(get_session)) -> TableResolveResponse:
    table = session.exec(select(RestaurantTable).where(RestaurantTable.qr_code_value == qr)).first()
    if table is None or table.status != TableStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='QR code not mapped to an active table.')
    return TableResolveResponse(id=table.id, table_number=table.table_number, status=table.status, qr_code_value=table.qr_code_value)


@router.post('/table/assign', response_model=TableSessionResponse)
def assign_table(
    payload: TableAssignmentRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> TableSessionResponse:
    customer = get_customer(principal, session)
    table = session.exec(select(RestaurantTable).where(RestaurantTable.qr_code_value == payload.qr_code_value)).first()
    if table is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='QR code not mapped to an active table.')
    ensure_table_available(session, table, allow_override=False)
    table_session = TableSession(table_id=table.id, customer_id=customer.id, assigned_by_role='CUSTOMER', assigned_by_id=customer.id)
    session.add(table_session)
    session.flush()
    record_audit(session, 'CUSTOMER', customer.id, 'customer.table.assigned', 'table_session', table_session.id, {'table_id': table.id})
    session.commit()
    return TableSessionResponse(
        id=table_session.id,
        table_id=table.id,
        table_number=table.table_number,
        customer_id=customer.id,
        customer_mobile_number=customer.mobile_number,
        started_at=table_session.started_at,
        ended_at=table_session.ended_at,
        status=table_session.status,
    )


@router.get('/menu', response_model=list[MenuItemResponse])
def get_customer_menu(
    foodType: FoodType | None = Query(default=None),
    available: bool = Query(default=True),
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> list[MenuItemResponse]:
    customer = get_customer(principal, session)
    active_session = session.exec(
        select(TableSession).where(
            TableSession.customer_id == customer.id,
            TableSession.status == TableSessionStatus.ACTIVE,
        )
    ).first()
    if active_session is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Customer must have an active table assignment.')
    statement = select(MenuItem)
    if available:
        statement = statement.where(MenuItem.is_available.is_(True))
    if foodType:
        statement = statement.where(MenuItem.food_type == foodType)
    items = session.exec(statement.order_by(MenuItem.name)).all()
    category_map = fetch_category_map(session)
    return [MenuItemResponse.model_validate(build_menu_item_response(item, category_map)) for item in items]


@router.get('/menu-categories', response_model=list[MenuCategoryResponse])
def list_menu_categories(session: Session = Depends(get_session)) -> list[MenuCategoryResponse]:
    categories = session.exec(select(MenuCategory).where(MenuCategory.is_active.is_(True))).all()
    return [MenuCategoryResponse(id=category.id, name=category.name, is_active=category.is_active) for category in categories]
