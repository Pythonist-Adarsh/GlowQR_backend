import os

with open('routers/auth.py', 'r', encoding='utf-8') as f:
    data = f.read()

target = """    if "email" in update_data:
        # Should verify email uniqueness ideally, but keeping simple
        current_user.email = update_data["email"]
    db.commit()
    return {"status": "ok"}"""

replacement = """    email_changed = False
    if "email" in update_data and update_data["email"] != current_user.email:
        current_user.email = update_data["email"]
        email_changed = True
    db.commit()
    
    if email_changed:
        access_token = security_auth.create_access_token(data={"sub": current_user.email})
        return {"status": "ok", "new_token": access_token}
    return {"status": "ok"}"""

data = data.replace(target, replacement)

with open('routers/auth.py', 'w', encoding='utf-8') as f:
    f.write(data)
print('Patched auth.py')
