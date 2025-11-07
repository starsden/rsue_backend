from fastapi import FastAPI
from app.routers.router import router
from app.core.core import engine, Base

app = FastAPI(title="RSUE Backend", description="rsue.devoriole.ru", docs_url="/")
Base.metadata.create_all(bind=engine)
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)