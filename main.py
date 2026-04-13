from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.reviews import router as reviews_router
from api.widget import router as widget_router
from api.share import router as share_router
from api.webhooks import router as webhooks_router
from services.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Review Sync Plugin",
    description="Aggregate and sync reviews from Google, Facebook, Yelp, and your website",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reviews_router, prefix="/api")
app.include_router(widget_router)
app.include_router(share_router, prefix="/api")
app.include_router(webhooks_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": "Review Sync Plugin",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "reviews": "/api/reviews",
            "stats": "/api/reviews/stats",
            "sync": "/api/sync",
            "widget": "/widget",
            "share": "/api/share",
        },
    }
