from database import engine, Base
import models

def main():
    print("Creating contact_messages table if it doesn't exist...")
    Base.metadata.create_all(bind=engine)
    print("Done.")

if __name__ == "__main__":
    main()
