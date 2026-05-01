"""Gerazão de PDF do checklist (reportlab).

Suporta tanto fotos em base64 (legado) quanto URLs (Cloudinary):
se `photo.url` está setado, baixa via HTTP; senão usa `photo.base64`.
"""
import base64 as _b64
from io import BytesIO
from typing import Optional

from fastapi import HTTPException

from core.storage import fetch_url_as_bytes, base64_to_bytes


def _get_image_bytes(item: dict) -> Optional[bytes]:
    """Aceita {url} ou {base64} e retorna bytes da imagem."""
    url = item.get("url")
    if url:
        b = fetch_url_as_bytes(url)
        if b is not None:
            return b
    return base64_to_bytes(item.get("base64", "") or "")


def render_checklist_pdf(doc: dict) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors as rc
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RImage
    except ImportError:
        raise HTTPException(status_code=500, detail="reportlab não instalado")

    buf = BytesIO()
    pdf = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], textColor=rc.HexColor("#0A0A0A"), fontSize=20, alignment=0)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=rc.HexColor("#0A0A0A"), fontSize=14, spaceBefore=10)
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=10, textColor=rc.HexColor("#222"))
    small = ParagraphStyle("small", parent=styles["BodyText"], fontSize=8, textColor=rc.HexColor("#555"))

    story = []
    story.append(Paragraph(f"<b>VALE</b><font color='#D4B000'><b>TECK</b></font> — Checklist de Instalação", h1))
    story.append(Paragraph(f"Nº <b>{doc.get('numero','')}</b> • Status: <b>{(doc.get('status') or '').upper()}</b>", body))
    story.append(Paragraph(f"Emitido em: {doc.get('sent_at') or doc.get('created_at')}", small))
    story.append(Spacer(1, 12))

    # Cliente
    story.append(Paragraph("Cliente", h2))
    tbl = Table([
        ["Nome", f"{doc.get('nome','')} {doc.get('sobrenome','')}"],
        ["Placa", doc.get("placa", "")],
        ["Telefone", doc.get("telefone") or "—"],
        ["Observações", doc.get("obs_iniciais") or "—"],
    ], colWidths=[4 * cm, 12 * cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), rc.HexColor("#F0F3F7")),
        ("GRID", (0, 0), (-1, -1), 0.3, rc.HexColor("#CCCCCC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(tbl)

    # Instalação
    story.append(Paragraph("Instalação", h2))
    bat = f"{doc.get('battery_state','—')}" + (f" • {doc.get('battery_voltage')}V" if doc.get("battery_voltage") else "")
    tbl = Table([
        ["Empresa", doc.get("empresa", "")],
        ["Equipamento", doc.get("equipamento", "")],
        ["Tipo", doc.get("tipo_atendimento") or "—"],
        ["IMEI", doc.get("imei") or "—"],
        ["ICCID", doc.get("iccid") or "—"],
        ["Acessórios", ", ".join(doc.get("acessorios") or []) or "—"],
        ["Bateria", bat],
        ["Tempo execução", f"{(doc.get('execution_elapsed_sec') or 0) // 60} min" if doc.get("execution_elapsed_sec") else "—"],
        ["Dispositivo", "✔ Online" if doc.get("device_online") is True else "✘ Offline" if doc.get("device_online") is False else "Não testado"],
    ], colWidths=[4 * cm, 12 * cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), rc.HexColor("#F0F3F7")),
        ("GRID", (0, 0), (-1, -1), 0.3, rc.HexColor("#CCCCCC")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(tbl)

    # Fotos
    photos = doc.get("photos") or []
    if photos:
        story.append(Paragraph(f"Evidências ({len(photos)} fotos)", h2))
        thumbs = []
        for p in photos[:8]:
            try:
                img_bytes = _get_image_bytes(p)
                if not img_bytes:
                    continue
                img = RImage(BytesIO(img_bytes), width=4 * cm, height=3 * cm)
                thumbs.append([img, Paragraph(p.get("label", ""), small)])
            except Exception:
                continue
        if thumbs:
            rows = []
            for i in range(0, len(thumbs), 2):
                row = [thumbs[i]]
                if i + 1 < len(thumbs):
                    row.append(thumbs[i + 1])
                else:
                    row.append("")
                rows.append(row)
            tbl = Table(rows, colWidths=[8 * cm, 8 * cm])
            tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
            story.append(tbl)

    # Assinatura
    sig_url = doc.get("signature_url") or ""
    sig_b64 = doc.get("signature_base64") or ""
    sig_bytes: Optional[bytes] = None
    if sig_url:
        sig_bytes = fetch_url_as_bytes(sig_url)
    if not sig_bytes and sig_b64:
        sig_bytes = base64_to_bytes(sig_b64)
    if sig_bytes:
        story.append(Paragraph("Assinatura do cliente", h2))
        try:
            story.append(RImage(BytesIO(sig_bytes), width=8 * cm, height=3 * cm))
            story.append(Paragraph(f"<i>{doc.get('nome','')} {doc.get('sobrenome','')}</i>", small))
        except Exception:
            pass

    # Alertas
    alerts = doc.get("alerts") or []
    if alerts:
        story.append(Paragraph("Alertas", h2))
        for a in alerts:
            story.append(Paragraph(f"• {a}", body))

    pdf.build(story)
    return buf.getvalue()
