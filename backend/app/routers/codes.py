from io import BytesIO

import qrcode
from barcode import Code128
from barcode.writer import SVGWriter
from fastapi import APIRouter, HTTPException, Response

router = APIRouter(prefix="/api/codes", tags=["qr & barcodes"])
CACHE = {"Cache-Control": "public, max-age=86400"}


@router.get("/qr")
def qr_code(text: str, size: int = 8):
    """PNG QR code for a membership no or book acc no."""
    if not text:
        raise HTTPException(400, "text is required")
    img = qrcode.make(text, box_size=max(2, min(size, 20)), border=2)
    buf = BytesIO()
    img.save(buf)
    return Response(buf.getvalue(), media_type="image/png", headers=CACHE)


@router.get("/barcode")
def barcode(text: str, show_text: bool = False):
    """SVG Code128 barcode (works with every 1D barcode scanner)."""
    if not text:
        raise HTTPException(400, "text is required")
    buf = BytesIO()
    Code128(text, writer=SVGWriter()).write(
        buf, options={"module_height": 8, "font_size": 8, "text_distance": 4, "quiet_zone": 1,
                 "write_text": show_text}
    )
    return Response(buf.getvalue(), media_type="image/svg+xml", headers=CACHE)
