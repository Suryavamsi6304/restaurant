from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.database import get_session
from app.core.security import Principal, require_roles
from app.models import Customer, MenuCategory, MenuItem, RestaurantTable, StaffRole, TableSession, TableSessionStatus
from app.schemas import MenuItemResponse, TableSessionResponse, WaitressOffboardRequest, WaitressRegisterCustomerRequest
from app.services import build_menu_item_response, ensure_table_available, fetch_category_map, get_or_create_customer, record_audit

router = APIRouter(prefix='/waitress', tags=['waitress'])
settings = get_settings()


@router.get('/menu', response_model=list[MenuItemResponse])
def get_live_menu(
    _: Principal = Depends(require_roles(StaffRole.WAITRESS, StaffRole.ADMIN)),
    session: Session = Depends(get_session),
) -> list[MenuItemResponse]:
    items = session.exec(select(MenuItem).order_by(MenuItem.name)).all()
    category_map = fetch_category_map(session)
    return [MenuItemResponse.model_validate(build_menu_item_response(item, category_map)) for item in items]


@router.get('/tables/status', response_model=list[TableSessionResponse])
def get_table_status(
    _: Principal = Depends(require_roles(StaffRole.WAITRESS, StaffRole.ADMIN)),
    session: Session = Depends(get_session),
) -> list[TableSessionResponse]:
    tables = session.exec(select(RestaurantTable)).all()
    active_sessions = session.exec(select(TableSession).where(TableSession.status == TableSessionStatus.ACTIVE)).all()
    customer_map = {customer.id: customer for customer in session.exec(select(Customer)).all()}
    session_map = {active_session.table_id: active_session for active_session in active_sessions}
    responses: list[TableSessionResponse] = []
    for table in tables:
        active_session = session_map.get(table.id)
        if active_session is None:
            responses.append(
                TableSessionResponse(
                    id=0,
                    table_id=table.id,
                    table_number=table.table_number,
                    customer_id=0,
                    customer_mobile_number='FREE',
                    started_at=table.created_at,
                    ended_at=None,
                    status=TableSessionStatus.CLOSED,
                )
            )
            continue
        customer = customer_map[active_session.customer_id]
        responses.append(
            TableSessionResponse(
                id=active_session.id,
                table_id=table.id,
                table_number=table.table_number,
                customer_id=customer.id,
                customer_mobile_number=customer.mobile_number,
                started_at=active_session.started_at,
                ended_at=active_session.ended_at,
                status=active_session.status,
            )
        )
    return responses


@router.post('/table/register-customer', response_model=TableSessionResponse, status_code=status.HTTP_201_CREATED)
def register_customer(
    payload: WaitressRegisterCustomerRequest,
    principal: Principal = Depends(require_roles(StaffRole.WAITRESS, StaffRole.ADMIN)),
    session: Session = Depends(get_session),
) -> TableSessionResponse:
    table = session.get(RestaurantTable, payload.table_id)
    if table is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Table not found.')
    allow_override = payload.override_active_session and settings.allow_waitress_override
    ensure_table_available(session, table, allow_override=allow_override)
    customer = get_or_create_customer(session, payload.mobile_number)
    customer.is_verified = True
    customer.updated_at = datetime.utcnow()
    table_session = TableSession(
        table_id=table.id,
        customer_id=customer.id,
        assigned_by_role=principal.role,
        assigned_by_id=principal.user_id,
    )
    session.add(customer)
    session.add(table_session)
    session.flush()
    record_audit(
        session,
        'USER',
        principal.user_id,
        'table.customer_registered',
        'table_session',
        table_session.id,
        {'table_id': table.id, 'mobile_number': customer.mobile_number, 'override': allow_override},
    )
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


@router.post('/table/offboard', response_model=TableSessionResponse)
def offboard_customer(
    payload: WaitressOffboardRequest,
    principal: Principal = Depends(require_roles(StaffRole.WAITRESS, StaffRole.ADMIN)),
    session: Session = Depends(get_session),
) -> TableSessionResponse:
    table_session = session.get(TableSession, payload.table_session_id)
    if table_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Table session not found.')
    if table_session.status == TableSessionStatus.CLOSED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Table session already closed.')
    table_session.status = TableSessionStatus.CLOSED
    table_session.ended_at = datetime.utcnow()
    table_session.offboarded_by = principal.user_id
    session.add(table_session)
    table = session.get(RestaurantTable, table_session.table_id)
    customer = session.get(Customer, table_session.customer_id)
    record_audit(session, 'USER', principal.user_id, 'table.customer_offboarded', 'table_session', table_session.id, {'table_id': table.id})
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
