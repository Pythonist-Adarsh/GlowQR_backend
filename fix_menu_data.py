from sqlalchemy.orm import Session
from database import SessionLocal
from models import Business

def fix_menu_data():
    db = SessionLocal()
    try:
        businesses = db.query(Business).all()
        updated_count = 0
        for b in businesses:
            if not b.menu_data and b.highlighted_dishes:
                is_non_food = b.category and b.category.lower() in ['tax / ca firm', 'education', 'bridal & festive jewellery', 'salon', 'spa', 'gym', 'medical', 'retail', 'hotel', 'jewellery', 'other']
                if is_non_food:
                    services_list = [s.strip() for s in b.highlighted_dishes.split('\n') if s.strip()]
                    if services_list:
                        new_menu_data = [{
                            "category": "Services",
                            "items": [
                                {
                                    "id": i,
                                    "name": svc,
                                    "emoji": "",
                                    "price": None
                                } for i, svc in enumerate(services_list)
                            ]
                        }]
                        b.menu_data = new_menu_data
                        updated_count += 1
                        print(f"Updated {b.name} ({b.category}) with {len(services_list)} services.")
        
        db.commit()
        print(f"Successfully updated {updated_count} businesses.")
    finally:
        db.close()

if __name__ == "__main__":
    fix_menu_data()
