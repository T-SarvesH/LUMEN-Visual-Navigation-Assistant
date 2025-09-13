from fastapi import FastAPI
from fastapi.middleware import CORSMiddleware


app = FastAPI(title="Lumen Application Programming interface")

app.add_middleware(

    CORSMiddleware,
    allowed_origins=["*"],
    allowed_headers=["*"],
    allowed_hosts=["*"],
    allowed_methods=["*"],
)


@app.get("/")
async def root():
    return {"message": "Welcome to Lumen API"}