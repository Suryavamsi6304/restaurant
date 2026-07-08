from sqlmodel import Session, select

from app.core.database import engine, init_db
from app.core.security import hash_password
from app.models import FoodType, MenuCategory, MenuItem, RestaurantTable, StaffRole, User
from app.services import generate_table_qr, seed_defaults


def seed_data() -> None:
    init_db()
    with Session(engine) as session:
        seed_defaults(session)
        admin = session.exec(select(User).where(User.username == 'admin')).first()
        if admin is None:
            admin = User(username='admin', role=StaffRole.ADMIN, password_hash=hash_password('Admin@123'))
            session.add(admin)
            session.commit()
            session.refresh(admin)
        for username, role in [('chef1', StaffRole.CHEF), ('waitress1', StaffRole.WAITRESS)]:
            existing = session.exec(select(User).where(User.username == username)).first()
            if existing is None:
                session.add(User(username=username, role=role, password_hash=hash_password('Password@123'), created_by=admin.id))
        if not session.exec(select(RestaurantTable)).all():
            session.add_all(
                [
                    RestaurantTable(table_number='T1', qr_code_value=generate_table_qr('T1')),
                    RestaurantTable(table_number='T2', qr_code_value=generate_table_qr('T2')),
                    RestaurantTable(table_number='T3', qr_code_value=generate_table_qr('T3')),
                ]
            )
        session.commit()
        categories = {category.name: category for category in session.exec(select(MenuCategory)).all()}
        if not session.exec(select(MenuItem)).all():
            session.add_all(
                [
                    MenuItem(name='Paneer Tikka', description='Char-grilled cottage cheese skewers.', price=10.99, category_id=categories['Starters'].id, food_type=FoodType.VEG, is_available=True, updated_by=admin.id),
                    MenuItem(name='Chicken Biryani', description='Fragrant rice with spiced chicken.', price=14.5, category_id=categories['Main Course'].id, food_type=FoodType.NON_VEG, is_available=True, updated_by=admin.id),
                    MenuItem(name='Masala Lemonade', description='Refreshing house-made lemonade.', price=4.25, category_id=categories['Beverages'].id, food_type=FoodType.VEG, is_available=True, updated_by=admin.id),
                ]
            )
        session.commit()


if __name__ == '__main__':
    seed_data()
