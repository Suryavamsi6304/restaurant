from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.database import get_session
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_otp_code,
    hash_otp,
    verify_password,
)
from app.models import Customer, OTPRequest, OTPStatus, RestaurantTable, StaffRole, TableSession, TableSessionStatus, User
from app.schemas import OTPRequestPayload, OTPRequestResponse, OTPVerifyPayload, RefreshRequest, StaffLoginRequest, TokenResponse
from app.services import ensure_staff_user, ensure_table_available, get_or_create_customer, record_audit

router = APIRouter(prefix='/auth', tags=['authentication'])
customer_router = APIRouter(prefix='/customer/auth', tags=['customer-authentication'])
settings = get_settings()


@router.post('/login', response_model=TokenResponse)
def login(payload: StaffLoginRequest, session: Session = Depends(get_session)) -> TokenResponse:
    user = session.exec(select(User).where(User.username == payload.username)).first()
    ensure_staff_user(user)
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid staff credentials.')
    access_token = create_access_token(user.username, user.role.value, user_id=user.id)
    refresh_token = create_refresh_token(user.username, user.role.value, user_id=user.id)
    record_audit(session, 'USER', user.id, 'staff.login', 'user', user.id, {'role': user.role.value})
    session.commit()
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, role=user.role.value)


@router.post('/refresh', response_model=TokenResponse)
def refresh_tokens(payload: RefreshRequest) -> TokenResponse:
    principal = decode_token(payload.refresh_token)
    if principal.token_type != 'refresh':
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Refresh token required.')
    access_token = create_access_token(principal.token_subject, principal.role, principal.user_id, principal.customer_id)
    refresh_token = create_refresh_token(principal.token_subject, principal.role, principal.user_id, principal.customer_id)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, role=principal.role)


@customer_router.post('/request-otp', response_model=OTPRequestResponse)
def request_otp(payload: OTPRequestPayload, session: Session = Depends(get_session)) -> OTPRequestResponse:
    latest_request = session.exec(
        select(OTPRequest)
        .where(OTPRequest.mobile_number == payload.mobile_number)
        .order_by(OTPRequest.created_at.desc())
    ).first()
    now = datetime.utcnow()
    if latest_request and (now - latest_request.created_at).total_seconds() < settings.otp_resend_cooldown_seconds:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail='OTP cooldown in progress.')
    otp_code = generate_otp_code()
    otp_request = OTPRequest(
        mobile_number=payload.mobile_number,
        otp_hash=hash_otp(otp_code),
        expires_at=now + timedelta(minutes=settings.otp_expire_minutes),
    )
    session.add(otp_request)
    record_audit(session, 'CUSTOMER', None, 'customer.otp.requested', 'otp_request', None, {'mobile_number': payload.mobile_number})
    session.commit()
    return OTPRequestResponse(
        message='OTP generated successfully.',
        expires_in_seconds=settings.otp_expire_minutes * 60,
        otp_code=otp_code if settings.demo_otp_passthrough else None,
    )


@customer_router.post('/verify-otp', response_model=TokenResponse)
def verify_otp(payload: OTPVerifyPayload, session: Session = Depends(get_session)) -> TokenResponse:
    otp_request = session.exec(
        select(OTPRequest)
        .where(OTPRequest.mobile_number == payload.mobile_number)
        .order_by(OTPRequest.created_at.desc())
    ).first()
    if otp_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='OTP request not found.')
    if otp_request.status == OTPStatus.LOCKED:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail='OTP request locked.')
    if otp_request.expires_at < datetime.utcnow():
        otp_request.status = OTPStatus.EXPIRED
        session.add(otp_request)
        session.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='OTP expired.')
    if otp_request.otp_hash != hash_otp(payload.otp_code):
        otp_request.attempts += 1
        if otp_request.attempts >= settings.otp_max_attempts:
            otp_request.status = OTPStatus.LOCKED
        session.add(otp_request)
        session.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid OTP code.')

    customer = get_or_create_customer(session, payload.mobile_number)
    customer.is_verified = True
    customer.last_login_at = datetime.utcnow()
    customer.updated_at = datetime.utcnow()
    otp_request.status = OTPStatus.VERIFIED
    session.add(customer)
    session.add(otp_request)
    if payload.qr_code_value:
        table = session.exec(select(RestaurantTable).where(RestaurantTable.qr_code_value == payload.qr_code_value)).first()
        if table is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='QR code not mapped to an active table.')
        ensure_table_available(session, table, allow_override=False)
        customer_session = TableSession(table_id=table.id, customer_id=customer.id, assigned_by_role='SYSTEM')
        session.add(customer_session)
        session.flush()
        record_audit(
            session,
            'CUSTOMER',
            customer.id,
            'customer.table.assigned',
            'table_session',
            customer_session.id,
            {'table_id': table.id, 'table_number': table.table_number},
        )
    record_audit(session, 'CUSTOMER', customer.id, 'customer.otp.verified', 'customer', customer.id, {'mobile_number': customer.mobile_number})
    session.commit()
    access_token = create_access_token(customer.mobile_number, 'CUSTOMER', customer_id=customer.id)
    refresh_token = create_refresh_token(customer.mobile_number, 'CUSTOMER', customer_id=customer.id)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, role='CUSTOMER')
