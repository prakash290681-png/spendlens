from dotenv import load_dotenv
load_dotenv()
import os
print("CLIENT_ID:", os.getenv("GOOGLE_CLIENT_ID"))
print("REDIRECT:", os.getenv("GOOGLE_REDIRECT_URI"))
from fastapi import FastAPI
from auth import router as auth_router

app = FastAPI()

app.include_router(auth_router)

@app.get("/")
def health_check():
    return {"status": "SpendLens backend is running 🚀"}
