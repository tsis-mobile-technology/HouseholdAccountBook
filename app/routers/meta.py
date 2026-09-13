from typing import List
from fastapi import APIRouter
from app.database.connection import get_connection, get_db_cursor
from app.models.schemas import CategoryModel, CategoryCreate, PaymentMethodModel
from app.core.network import get_local_ip, get_mobile_access_url, get_qr_base64
from app.core.config import PORT

router = APIRouter(prefix="/api/meta", tags=["Metadata"])

@router.get("/categories", response_model=List[CategoryModel])
def get_categories():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, color_hex, icon, sort_order, is_active FROM categories WHERE is_active = 1 ORDER BY sort_order ASC, id ASC")
        rows = cur.fetchall()
        return [CategoryModel(**dict(r)) for r in rows]
    finally:
        conn.close()

@router.post("/categories", response_model=dict)
def add_category(cat: CategoryCreate):
    with get_db_cursor() as cur:
        cur.execute("""
            INSERT INTO categories (name, color_hex, icon, sort_order)
            VALUES (?, ?, ?, ?)
        """, (cat.name, cat.color_hex, cat.icon, cat.sort_order))
        return {"status": "success", "id": cur.lastrowid}

@router.get("/payment-methods", response_model=List[PaymentMethodModel])
def get_payment_methods():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, is_active FROM payment_methods WHERE is_active = 1 ORDER BY id ASC")
        rows = cur.fetchall()
        return [PaymentMethodModel(**dict(r)) for r in rows]
    finally:
        conn.close()

@router.get("/network-info")
def get_network_info():
    local_ip = get_local_ip()
    mobile_url = get_mobile_access_url()
    qr_base64 = get_qr_base64(mobile_url)
    return {
        "local_ip": local_ip,
        "port": PORT,
        "pc_url": f"http://localhost:{PORT}",
        "mobile_url": mobile_url,
        "qr_code": qr_base64
    }
