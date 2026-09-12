"""List existing domains, so the frontend can populate a dropdown."""

from fastapi import APIRouter

from app.models.schemas import DomainInfo
from app.services import vector_store

router = APIRouter(prefix="/api", tags=["domains"])


@router.get("/domains", response_model=list[DomainInfo])
async def get_domains():
    domains = vector_store.list_domains()
    return [
        DomainInfo(name=d["name"], document_count=0, chunk_count=d["chunk_count"])
        for d in domains
    ]
