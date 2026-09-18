import sys
sys.path.append('d:/glowQR/backend')
from database import engine, Base
import models

def main():
    print("Creating AI Generation Events table...")
    models.AIGenerationEvent.__table__.create(engine, checkfirst=True)
    print("Success!")

if __name__ == "__main__":
    main()
