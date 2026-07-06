from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.db.seed import seed_database
import uvicorn

app = FastAPI(
    title="BallMetrix Backend API",
    description="Football Predictor and MLOps Dashboard Service",
    version="1.0.0"
)

# Enable CORS for frontend dashboard connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    print("Initializing Database & Seeding initial data...")
    seed_database()

app.include_router(router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to BallMetrix API service!"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
