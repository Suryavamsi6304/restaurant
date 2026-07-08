from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.database import get_session
from app.main import app


@pytest.fixture()
def client(tmp_path: Path):
    database_path = tmp_path / 'test.db'
    engine = create_engine(f'sqlite:///{database_path}', connect_args={'check_same_thread': False})
    SQLModel.metadata.create_all(engine)

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    with Session(engine) as session:
        from app.services import seed_defaults
        from app.core.security import hash_password
        from app.models import FoodType, MenuCategory, MenuItem, RestaurantTable, StaffRole, User
        from app.services import generate_table_qr

        seed_defaults(session)
        admin = User(username='admin', role=StaffRole.ADMIN, password_hash=hash_password('Admin@123'))
        chef = User(username='chef1', role=StaffRole.CHEF, password_hash=hash_password('Password@123'), created_by=1)
        waitress = User(username='waitress1', role=StaffRole.WAITRESS, password_hash=hash_password('Password@123'), created_by=1)
        session.add(admin)
        session.commit()
        session.refresh(admin)
        chef.created_by = admin.id
        waitress.created_by = admin.id
        session.add(chef)
        session.add(waitress)
        session.commit()
        categories = {category.name: category for category in session.exec(select(MenuCategory)).all()}
        table = RestaurantTable(table_number='T1', qr_code_value=generate_table_qr('T1'))
        item = MenuItem(
            name='Paneer Tikka',
            description='Char-grilled cottage cheese skewers.',
            price=10.99,
            category_id=categories['Starters'].id,
            food_type=FoodType.VEG,
            is_available=True,
            updated_by=admin.id,
        )
        session.add(table)
        session.add(item)
        session.commit()
        session.refresh(table)
        session.refresh(item)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def auth_headers(token: str) -> dict[str, str]:
    return {'Authorization': f'******'}


def staff_login(client: TestClient, username: str, password: str) -> str:
    response = client.post('/api/v1/auth/login', json={'username': username, 'password': password})
    assert response.status_code == 200
    return response.json()['access_token']


def test_admin_can_create_user_and_table(client: TestClient):
    token = staff_login(client, 'admin', 'Admin@123')
    headers = auth_headers(token)
    create_user = client.post('/api/v1/admin/users', json={'role': 'CHEF', 'username': 'chef2', 'password': 'Password@123'}, headers=headers)
    assert create_user.status_code == 201
    create_table = client.post('/api/v1/admin/tables', json={'table_number': 'T2'}, headers=headers)
    assert create_table.status_code == 201


def test_customer_qr_otp_menu_flow(client: TestClient):
    admin_token = staff_login(client, 'admin', 'Admin@123')
    tables = client.get('/api/v1/admin/tables', headers=auth_headers(admin_token))
    qr_code = tables.json()[0]['qr_code_value']
    resolve = client.get('/api/v1/customer/table/resolve', params={'qr': qr_code})
    assert resolve.status_code == 200
    request_otp = client.post('/api/v1/customer/auth/request-otp', json={'mobile_number': '9999999999'})
    assert request_otp.status_code == 200
    otp_code = request_otp.json()['otp_code']
    verify = client.post('/api/v1/customer/auth/verify-otp', json={'mobile_number': '9999999999', 'otp_code': otp_code, 'qr_code_value': resolve.json()['qr_code_value']})
    assert verify.status_code == 200
    customer_headers = auth_headers(verify.json()['access_token'])
    menu = client.get('/api/v1/customer/menu', headers=customer_headers)
    assert menu.status_code == 200
    assert menu.json()[0]['name'] == 'Paneer Tikka'


def test_chef_can_toggle_availability_and_waitress_can_offboard(client: TestClient):
    chef_token = staff_login(client, 'chef1', 'Password@123')
    chef_headers = auth_headers(chef_token)
    menu_items = client.get('/api/v1/chef/menu-items', headers=chef_headers)
    item_id = menu_items.json()[0]['id']
    toggle = client.patch(f'/api/v1/chef/menu-items/{item_id}/availability', json={'is_available': False, 'stock_qty': 0}, headers=chef_headers)
    assert toggle.status_code == 200
    assert toggle.json()['is_available'] is False
    waitress_token = staff_login(client, 'waitress1', 'Password@123')
    waitress_headers = auth_headers(waitress_token)
    admin_token = staff_login(client, 'admin', 'Admin@123')
    tables = client.get('/api/v1/admin/tables', headers=auth_headers(admin_token)).json()
    register = client.post('/api/v1/waitress/table/register-customer', json={'table_id': tables[0]['id'], 'mobile_number': '8888888888'}, headers=waitress_headers)
    assert register.status_code == 201
    offboard = client.post('/api/v1/waitress/table/offboard', json={'table_session_id': register.json()['id']}, headers=waitress_headers)
    assert offboard.status_code == 200
    assert offboard.json()['status'] == 'CLOSED'
