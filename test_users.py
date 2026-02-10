from database import SessionLocal
from models import User

db = SessionLocal()

user = User(email="ayu.jaiswal@gmail.com", name="Wife")
db.add(user)
db.commit()

print("User created:", user.id)
