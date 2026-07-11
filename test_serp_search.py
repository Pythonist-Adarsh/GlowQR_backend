import os
from dotenv import load_dotenv
load_dotenv()
import services.serpapi_service as serpapi

details = serpapi.fetch_place_details("ChIJ89TtKbn7mzkRlGfoRYDgSXA")
print(details)
