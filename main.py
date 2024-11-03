from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from database import create_engine, Base, engine
from fastapi.middleware.cors import CORSMiddleware
import models
from router import products, users, payment


app = FastAPI()

models.Base.metadata.create_all(bind=engine)
app.mount("/images", StaticFiles(directory="images"), name="images")

origins = [
    "http://localhost:3000",
    "https://myfrontenddomain.com"
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allow only specified origins
    allow_credentials=True,  # Allow cookies and authentication headers
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"]  # Allow all headers
)






app.include_router(products.router)
app.include_router(users.router)
app.include_router(payment.router)


