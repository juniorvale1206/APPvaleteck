"""Geração de PDF do Fechamento Mensal (reportlab)."""
from io import BytesIO
from typing import Optional

from fastapi import HTTPException


def render_closure_pdf(user: dict, closure: dict) -> bytes:
    """Renderiza PDF do fechamento mensal.

    Espera `closure` com shape: { user_id, month, confirmed_at, breakdown: {...}, signature_base64? }
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors as rc
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    except ImportError:
        raise HTTPException(status_code=500, detail="reportlab não instalado")

    buf = BytesIO()
    pdf = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], textColor=rc.HexColor("#0A0A0A"), fontSize=20)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=rc.HexColor("#0A0A0A"), fontSize=14, spaceBefore=12)
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=10)
    small = ParagraphStyle("small", parent=styles["BodyText"], fontSize=8, textColor=rc.HexColor("#555"))

    bd = closure.get("breakdown", {})
    confirmed = closure.get("confirmed_at")
    month = closure.get("month", "")

    story = []
    story.append(Paragraph(
        f"<b>VALE</b><font color='#D4B000'><b>TECK</b></font> — Fechamento Mensal",
        h1,
    ))
    story.append(Paragraph(f"Técnico: <b>{user.get('name','—')}</b> • {user.get('email','—')}", body))
    story.append(Paragraph(f"Mês: <b>{month}</b>", body))
    if confirmed:
        story.append(Paragraph(f"Status: <b>CONFIRMADO</b> em {confirmed}", small))
    else:
        story.append(Paragraph("Status: <b>EM ABERTO</b> (snapshot em tempo real)", small))
    story.append(Spacer(1, 8))

    # Resumo financeiro
    story.append(Paragraph("Resumo", h2))
    rows = [
        ["Nível do técnico", (bd.get("level") or "—").upper()],
        ["OS enviadas no mês", str(bd.get("total_jobs", 0))],
        ["Itens em estoque", str(bd.get("inventory_total", 0))],
        ["Itens vencidos", str(bd.get("overdue_count", 0))],
        ["Ganhos brutos (motor)", f"R$ {bd.get('total_gross', 0):.2f}"],
        ["Bônus mensal (nível)", f"+ R$ {(bd.get('bonuses') or {}).get('bonus_total', 0):.2f}"],
        ["Penalidades", f"- R$ {bd.get('penalty_total', 0):.2f}"],
        ["Líquido final", f"R$ {bd.get('net_after_penalty', 0):.2f}"],
    ]
    tbl = Table(rows, colWidths=[8 * cm, 8 * cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), rc.HexColor("#F0F3F7")),
        ("GRID", (0, 0), (-1, -1), 0.3, rc.HexColor("#CCCCCC")),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 5), (-1, 5), rc.HexColor("#E8F5E9")),
        ("TEXTCOLOR", (0, 5), (-1, 5), rc.HexColor("#1B5E20")),
        ("BACKGROUND", (0, 6), (-1, 6), rc.HexColor("#FEF2F2")),
        ("TEXTCOLOR", (0, 6), (-1, 6), rc.HexColor("#991B1B")),
        ("BACKGROUND", (0, 7), (-1, 7), rc.HexColor("#FFF9E6")),
        ("FONTNAME", (0, 7), (-1, 7), "Helvetica-Bold"),
    ]))
    story.append(tbl)

    # Detalhe de bônus por nível
    bonuses = bd.get("bonuses") or {}
    if bonuses.get("bonus_total", 0) > 0:
        story.append(Paragraph("Bônus por nível", h2))
        brows = [["Item", "Valor"]]
        if bonuses.get("bonus_junior_meta"):
            brows.append(["Meta de 30 OS (Júnior)", f"R$ {bonuses['bonus_junior_meta']:.2f}"])
        if bonuses.get("bonus_junior_zero_returns"):
            brows.append(["0 retornos no mês (Júnior)", f"R$ {bonuses['bonus_junior_zero_returns']:.2f}"])
        if bonuses.get("bonus_n1n2_retroactive"):
            brows.append(
                [f"Meta 60 OS + {bonuses.get('within_sla_os', 0)} dentro SLA (×R$ 2 retro)",
                 f"R$ {bonuses['bonus_n1n2_retroactive']:.2f}"]
            )
        if bonuses.get("bonus_n3_residual"):
            brows.append([f"Residual instrutor ({bonuses.get('tutee_total_os', 0)} OS de juniores)",
                          f"R$ {bonuses['bonus_n3_residual']:.2f}"])
        if bonuses.get("bonus_n3_tutoria"):
            brows.append([f"Bônus tutoria ({bonuses.get('tutees_hit_goal', 0)} junior(es) bateu meta)",
                          f"R$ {bonuses['bonus_n3_tutoria']:.2f}"])
        if bonuses.get("tutees_with_returns", 0) > 0:
            brows.append([f"⚠️ Guilhotina tutoria ({bonuses['tutees_with_returns']} junior com retorno)",
                          "R$ 0,00 bloqueado"])
        btbl = Table(brows, colWidths=[11 * cm, 5 * cm])
        btbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), rc.HexColor("#0A0A0A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), rc.HexColor("#FFFFFF")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.3, rc.HexColor("#CCCCCC")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        story.append(btbl)

    # Itens vencidos
    overdue = bd.get("overdue_items") or []
    if overdue:
        story.append(Paragraph(f"Itens vencidos ({len(overdue)})", h2))
        head = ["Modelo", "Série / IMEI", "Placa", "Dias atrasado", "Valor"]
        data = [head]
        for it in overdue:
            ident = it.get("serie") or it.get("imei") or "—"
            data.append([
                it.get("modelo", "—"),
                ident,
                it.get("placa") or "—",
                str(it.get("days_overdue", 0)),
                f"R$ {float(it.get('equipment_value') or 0):.2f}",
            ])
        tbl = Table(data, colWidths=[5 * cm, 4 * cm, 2.5 * cm, 2.5 * cm, 2 * cm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), rc.HexColor("#0A0A0A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), rc.HexColor("#FFFFFF")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.3, rc.HexColor("#CCCCCC")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (-1, 1), (-1, -1), rc.HexColor("#991B1B")),
        ]))
        story.append(tbl)

    # Notas
    notes = closure.get("notes") or ""
    if notes:
        story.append(Paragraph("Observações", h2))
        story.append(Paragraph(notes, body))

    pdf.build(story)
    return buf.getvalue()
