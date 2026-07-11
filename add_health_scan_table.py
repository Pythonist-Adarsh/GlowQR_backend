from database import engine, Base
from models import HealthCheckScan

print("Creating HealthCheckScan table...")
Base.metadata.create_all(bind=engine, tables=[HealthCheckScan.__table__])
print("Done.")
