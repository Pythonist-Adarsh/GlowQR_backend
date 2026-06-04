
import sys; sys.path.append('d:/glowQR/backend');
from database import engine;
from sqlalchemy import text;
with engine.connect() as conn:
    conn.execute(text('ALTER TABLE scan_events ADD COLUMN IF NOT EXISTS review_language VARCHAR DEFAULT \'english\''))
    conn.commit()
print('Column added successfully!')

