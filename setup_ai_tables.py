from database import engine, Base
# Import all models to ensure they are registered with Base
import models
import models_ai

print("Creating AI tables...")
Base.metadata.create_all(bind=engine)
print("Done.")
