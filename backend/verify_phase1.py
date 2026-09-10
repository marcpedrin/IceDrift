import sys
sys.path.insert(0, '.')

from app.main import app
print("FastAPI app loaded OK")

from app.services.ingestion_service import get_ingestion
ing = get_ingestion()
ing._load_all_from_disk()
s = ing.status()
print("Icebergs:", s["icebergs_loaded"])
print("SIC cells:", s["sic_cells_loaded"])
print("Routes:", s["routes_loaded"])
print("GEBCO:", s["gebco_available"])
