from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.security import Principal, require_roles
from app.models import MenuCategory, MenuItem, StaffRole
from app.schemas import MenuAvailabilityRequest, MenuCategoryResponse, MenuItemCreateRequest, MenuItemResponse, MenuItemUpdateRequest
from app.services import build_menu_item_response, fetch_category_map, record_audit

router = APIRouter(prefix='/chef', tags=['chef'])


@router.get('/menu-categories', response_model=list[MenuCategoryResponse])
def list_categories(
    _: Principal = Depends(require_roles(StaffRole.CHEF, StaffRole.ADMIN, StaffRole.WAITRESS)),
    session: Session = Depends(get_session),
) -> list[MenuCategoryResponse]:
    categories = session.exec(select(MenuCategory).where(MenuCategory.is_active.is_(True))).all()
    return [MenuCategoryResponse(id=category.id, name=category.name, is_active=category.is_active) for category in categories]


@router.get('/menu-items', response_model=list[MenuItemResponse])
def list_menu_items(
    _: Principal = Depends(require_roles(StaffRole.CHEF, StaffRole.ADMIN, StaffRole.WAITRESS)),
    session: Session = Depends(get_session),
) -> list[MenuItemResponse]:
    items = session.exec(select(MenuItem).order_by(MenuItem.name)).all()
    category_map = fetch_category_map(session)
    return [MenuItemResponse.model_validate(build_menu_item_response(item, category_map)) for item in items]


@router.post('/menu-items', response_model=MenuItemResponse, status_code=status.HTTP_201_CREATED)
def create_menu_item(
    payload: MenuItemCreateRequest,
    principal: Principal = Depends(require_roles(StaffRole.CHEF, StaffRole.ADMIN)),
    session: Session = Depends(get_session),
) -> MenuItemResponse:
    if payload.category_id and session.get(MenuCategory, payload.category_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Category not found.')
    item = MenuItem(**payload.model_dump(), updated_by=principal.user_id)
    session.add(item)
    session.flush()
    record_audit(session, 'USER', principal.user_id, 'menu_item.created', 'menu_item', item.id, payload.model_dump())
    session.commit()
    category_map = fetch_category_map(session)
    return MenuItemResponse.model_validate(build_menu_item_response(item, category_map))


@router.put('/menu-items/{item_id}', response_model=MenuItemResponse)
def update_menu_item(
    item_id: int,
    payload: MenuItemUpdateRequest,
    principal: Principal = Depends(require_roles(StaffRole.CHEF, StaffRole.ADMIN)),
    session: Session = Depends(get_session),
) -> MenuItemResponse:
    item = session.get(MenuItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Menu item not found.')
    updates = payload.model_dump(exclude_unset=True)
    if 'category_id' in updates and updates['category_id'] and session.get(MenuCategory, updates['category_id']) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Category not found.')
    for field, value in updates.items():
        setattr(item, field, value)
    item.updated_by = principal.user_id
    item.updated_at = datetime.utcnow()
    session.add(item)
    record_audit(session, 'USER', principal.user_id, 'menu_item.updated', 'menu_item', item.id, updates)
    session.commit()
    category_map = fetch_category_map(session)
    return MenuItemResponse.model_validate(build_menu_item_response(item, category_map))


@router.patch('/menu-items/{item_id}/availability', response_model=MenuItemResponse)
def update_availability(
    item_id: int,
    payload: MenuAvailabilityRequest,
    principal: Principal = Depends(require_roles(StaffRole.CHEF, StaffRole.ADMIN)),
    session: Session = Depends(get_session),
) -> MenuItemResponse:
    item = session.get(MenuItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Menu item not found.')
    item.is_available = payload.is_available
    item.stock_qty = payload.stock_qty
    item.updated_by = principal.user_id
    item.updated_at = datetime.utcnow()
    session.add(item)
    record_audit(session, 'USER', principal.user_id, 'menu_item.availability_updated', 'menu_item', item.id, payload.model_dump())
    session.commit()
    category_map = fetch_category_map(session)
    return MenuItemResponse.model_validate(build_menu_item_response(item, category_map))


@router.delete('/menu-items/{item_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_menu_item(
    item_id: int,
    principal: Principal = Depends(require_roles(StaffRole.CHEF, StaffRole.ADMIN)),
    session: Session = Depends(get_session),
) -> None:
    item = session.get(MenuItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Menu item not found.')
    session.delete(item)
    record_audit(session, 'USER', principal.user_id, 'menu_item.deleted', 'menu_item', item.id, {'name': item.name})
    session.commit()
