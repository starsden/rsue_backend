from fastapi import FastAPI
from app.routers.router import router
from app.routers.orga_rt import orga
from app.core.core import engine, Base

app = FastAPI(title="RSUE Backend", description="rsue.devoriole.ru", docs_url="/", version="0.2.1")
Base.metadata.create_all(bind=engine)
app.include_router(router)
app.include_router(orga)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)