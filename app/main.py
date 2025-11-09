from fastapi import FastAPI
from app.routers.router import router
from app.routers.orga_rt import orga
from app.routers.sklads import sklad
from app.core.core import engine, Base
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="RSUE Backend", description="rsue.devoriole.ru", docs_url="/", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)
app.include_router(router)
app.include_router(orga)
app.include_router(sklad)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)