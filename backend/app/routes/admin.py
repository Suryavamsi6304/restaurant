from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.security import Principal, hash_password, require_roles
from app.models import AuditLog, Customer, RestaurantTable, StaffRole, TableSession, User
from app.schemas import (
    AuditLogResponse,
    PasswordResetRequest,
    TableCreateRequest,
    TableResponse,
    TableSessionResponse,
    TableUpdateRequest,
    UserCreateRequest,
    UserResponse,
    UserStatusUpdateRequest,
    UserUpdateRequest,
)
from app.services import generate_table_qr, record_audit

router = APIRouter(prefix='/admin', tags=['admin'])


@router.get('/users', response_model=list[UserResponse])
def list_users(
    _: Principal = Depends(require_roles(StaffRole.ADMIN)),
    session: Session = Depends(get_session),
) -> list[UserResponse]:
    users = session.exec(select(User).order_by(User.created_at.desc())).all()
    return [UserResponse(id=user.id, username=user.username, role=user.role, status=user.status, created_at=user.created_at) for user in users]


@router.post('/users', response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreateRequest,
    principal: Principal = Depends(require_roles(StaffRole.ADMIN)),
    session: Session = Depends(get_session),
) -> UserResponse:
    if payload.role == StaffRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Admin self-provisioning is not allowed from this endpoint.')
    existing = session.exec(select(User).where(User.username == payload.username)).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Username already exists.')
    user = User(
        username=payload.username,
        role=payload.role,
        password_hash=hash_password(payload.password),
        created_by=principal.user_id,
    )
    session.add(user)
    session.flush()
    record_audit(session, 'USER', principal.user_id, 'admin.user_created', 'user', user.id, {'role': user.role.value, 'username': user.username})
    session.commit()
    return UserResponse(id=user.id, username=user.username, role=user.role, status=user.status, created_at=user.created_at)


@router.put('/users/{user_id}', response_model=UserResponse)
def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    principal: Principal = Depends(require_roles(StaffRole.ADMIN)),
    session: Session = Depends(get_session),
) -> UserResponse:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found.')
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(user, field, value)
    user.updated_at = datetime.utcnow()
    session.add(user)
    record_audit(session, 'USER', principal.user_id, 'admin.user_updated', 'user', user.id, updates)
    session.commit()
    return UserResponse(id=user.id, username=user.username, role=user.role, status=user.status, created_at=user.created_at)


@router.patch('/users/{user_id}/status', response_model=UserResponse)
def update_user_status(
    user_id: int,
    payload: UserStatusUpdateRequest,
    principal: Principal = Depends(require_roles(StaffRole.ADMIN)),
    session: Session = Depends(get_session),
) -> UserResponse:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found.')
    user.status = payload.status
    user.updated_at = datetime.utcnow()
    session.add(user)
    record_audit(session, 'USER', principal.user_id, 'admin.user_status_updated', 'user', user.id, {'status': payload.status.value})
    session.commit()
    return UserResponse(id=user.id, username=user.username, role=user.role, status=user.status, created_at=user.created_at)


@router.post('/users/{user_id}/reset-password', response_model=UserResponse)
def reset_password(
    user_id: int,
    payload: PasswordResetRequest,
    principal: Principal = Depends(require_roles(StaffRole.ADMIN)),
    session: Session = Depends(get_session),
) -> UserResponse:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found.')
    user.password_hash = hash_password(payload.password)
    user.updated_at = datetime.utcnow()
    session.add(user)
    record_audit(session, 'USER', principal.user_id, 'admin.user_password_reset', 'user', user.id, {'username': user.username})
    session.commit()
    return UserResponse(id=user.id, username=user.username, role=user.role, status=user.status, created_at=user.created_at)


@router.get('/tables', response_model=list[TableResponse])
def list_tables(
    _: Principal = Depends(require_roles(StaffRole.ADMIN)),
    session: Session = Depends(get_session),
) -> list[TableResponse]:
    tables = session.exec(select(RestaurantTable).order_by(RestaurantTable.table_number)).all()
    return [TableResponse(id=table.id, table_number=table.table_number, qr_code_value=table.qr_code_value, status=table.status) for table in tables]


@router.post('/tables', response_model=TableResponse, status_code=status.HTTP_201_CREATED)
def create_table(
    payload: TableCreateRequest,
    principal: Principal = Depends(require_roles(StaffRole.ADMIN)),
    session: Session = Depends(get_session),
) -> TableResponse:
    existing = session.exec(select(RestaurantTable).where(RestaurantTable.table_number == payload.table_number)).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Table number already exists.')
    table = RestaurantTable(table_number=payload.table_number, qr_code_value=generate_table_qr(payload.table_number))
    session.add(table)
    session.flush()
    record_audit(session, 'USER', principal.user_id, 'admin.table_created', 'table', table.id, {'table_number': table.table_number})
    session.commit()
    return TableResponse(id=table.id, table_number=table.table_number, qr_code_value=table.qr_code_value, status=table.status)


@router.put('/tables/{table_id}', response_model=TableResponse)
def update_table(
    table_id: int,
    payload: TableUpdateRequest,
    principal: Principal = Depends(require_roles(StaffRole.ADMIN)),
    session: Session = Depends(get_session),
) -> TableResponse:
    table = session.get(RestaurantTable, table_id)
    if table is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Table not found.')
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(table, field, value)
    table.updated_at = datetime.utcnow()
    session.add(table)
    record_audit(session, 'USER', principal.user_id, 'admin.table_updated', 'table', table.id, updates)
    session.commit()
    return TableResponse(id=table.id, table_number=table.table_number, qr_code_value=table.qr_code_value, status=table.status)


@router.post('/tables/{table_id}/regenerate-qr', response_model=TableResponse)
def regenerate_qr(
    table_id: int,
    principal: Principal = Depends(require_roles(StaffRole.ADMIN)),
    session: Session = Depends(get_session),
) -> TableResponse:
    table = session.get(RestaurantTable, table_id)
    if table is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Table not found.')
    table.qr_code_value = generate_table_qr(table.table_number)
    table.updated_at = datetime.utcnow()
    session.add(table)
    record_audit(session, 'USER', principal.user_id, 'admin.table_qr_regenerated', 'table', table.id, {'table_number': table.table_number})
    session.commit()
    return TableResponse(id=table.id, table_number=table.table_number, qr_code_value=table.qr_code_value, status=table.status)


@router.get('/occupancy', response_model=list[TableSessionResponse])
def get_occupancy(
    _: Principal = Depends(require_roles(StaffRole.ADMIN)),
    session: Session = Depends(get_session),
) -> list[TableSessionResponse]:
    results = []
    sessions = session.exec(select(TableSession).order_by(TableSession.started_at.desc())).all()
    for table_session in sessions:
        table = session.get(RestaurantTable, table_session.table_id)
        customer = session.get(Customer, table_session.customer_id)
        results.append(
            TableSessionResponse(
                id=table_session.id,
                table_id=table.id,
                table_number=table.table_number,
                customer_id=customer.id,
                customer_mobile_number=customer.mobile_number,
                started_at=table_session.started_at,
                ended_at=table_session.ended_at,
                status=table_session.status,
            )
        )
    return results


@router.get('/audit-logs', response_model=list[AuditLogResponse])
def list_audit_logs(
    _: Principal = Depends(require_roles(StaffRole.ADMIN)),
    session: Session = Depends(get_session),
) -> list[AuditLogResponse]:
    logs = session.exec(select(AuditLog).order_by(AuditLog.created_at.desc())).all()
    return [
        AuditLogResponse(
            id=log.id,
            actor_type=log.actor_type,
            actor_id=log.actor_id,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            details=log.details,
            created_at=log.created_at,
        )
        for log in logs
    ]
