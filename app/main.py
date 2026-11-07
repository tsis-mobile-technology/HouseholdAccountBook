from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from app.core.config import STATIC_DIR, HOST, PORT
from app.core.network import print_terminal_qr
from app.core.backup import perform_daily_backup
from app.core.scheduler import start_scheduler, stop_scheduler
from app.database.schema import init_database
from app.routers import transactions, fixed_plans, analytics, spreadsheet, meta, gdrive, cards

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize DB schema and defaults
    init_database()
    # 2. Perform rolling backup if needed
    perform_daily_backup()
    # 3. Start background backup scheduler
    start_scheduler()
    # 4. Print QR code to terminal for instant mobile access
    print_terminal_qr()
    yield
    # Graceful shutdown
    stop_scheduler()

app = FastAPI(
    title="HouseholdAccountBook",
    description="스마트 파스텔 가계부 API & Web App",
    version="1.1.0",
    lifespan=lifespan
)

# CORS middleware for LAN access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(transactions.router)
app.include_router(fixed_plans.router)
app.include_router(analytics.router)
app.include_router(spreadsheet.router)
app.include_router(meta.router)
app.include_router(gdrive.router)
app.include_router(cards.router)

# Mount static assets
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_index():
    return FileResponse(STATIC_DIR / "index.html")

if __name__ == "__main__":
    import uvicorn
    from app.core.config import USE_HTTPS, SSL_CERTFILE, SSL_KEYFILE, SSL_KEYFILE_PASSWORD

    ssl_kwargs = {}
    if USE_HTTPS:
        ssl_kwargs["ssl_certfile"] = SSL_CERTFILE
        ssl_kwargs["ssl_keyfile"] = SSL_KEYFILE
        if SSL_KEYFILE_PASSWORD:
            ssl_kwargs["ssl_keyfile_password"] = SSL_KEYFILE_PASSWORD

    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False, **ssl_kwargs)
