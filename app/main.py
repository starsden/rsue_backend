from fastapi import FastAPI
from app.routers.router import router
from app.routers.orga_rt import orga
from app.routers.sklads import sklad
from app.routers.nomen_rt import nomen
from app.routers.report_rt import pdf
from app.routers.stock_rt import stockk
from app.routers.sklad_docs_rt import docs
from app.core.core import engine, Base
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="RSUE Backend", description="## Otter greets you!\n\nrsue.devoriole.ru", docs_url="/papers", version="0.4.0")
app.mount("/static", StaticFiles(directory="static"), name="static")

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
app.include_router(nomen)
app.include_router(pdf)
app.include_router(stockk)
app.include_router(docs)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)