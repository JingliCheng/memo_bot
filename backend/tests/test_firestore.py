import os, time
from dotenv import load_dotenv
from google.cloud import firestore

load_dotenv()
db = firestore.Client(project=os.getenv("FIRESTORE_PROJECT"))  # or firestore.Client()
print("Project:", db.project)

doc = db.collection("smoketest").document("hello")
doc.set({"ts": time.time(), "msg": "it works"})
print("Read back:", doc.get().to_dict())
