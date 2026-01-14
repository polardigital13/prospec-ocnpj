from datetime import datetime
from database import get_conn, log_event
from utils import today_str
from segmentation import segmento_por_cnae
from cnpj_scraper import fetch_offices_by_founded_range, extract_items, normalize_office
from whatsapp_sender import notify_admin_new_lead


def capture_job():
    """Captura leads da API CNPJA dos últimos 30 dias e insere no banco."""
    from datetime import timedelta

    hoje = today_str()
    trinta_dias_atras = (
        __import__("datetime").datetime.fromisoformat(hoje) - timedelta(days=30)
    ).strftime("%Y-%m-%d")

    inserted = 0
    total = 0
    page_num = 0

    with get_conn() as conn:
        payload = fetch_offices_by_founded_range(trinta_dias_atras, hoje)
        items = extract_items(payload)

        if items:
            for it in items:
                lead = normalize_office(it)
                if not lead.get("cnpj"):
                    continue

                seg = segmento_por_cnae(lead.get("cnae_principal"))
                try:
                    conn.execute(
                        """
                        INSERT INTO leads(
                            cnpj, razao_social, cidade, uf, cnae_principal,
                            telefone, email, endereco, data_abertura, segmento,
                            created_at, status
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'novo')
                    """,
                        (
                            lead["cnpj"],
                            lead["razao_social"],
                            lead["cidade"],
                            lead["uf"],
                            lead["cnae_principal"],
                            lead["telefone"],
                            lead["email"],
                            lead["endereco"],
                            lead["data_abertura"],
                            seg,
                            datetime.utcnow().isoformat(),
                        ),
                    )
                    inserted += 1
                    # Envia notificação para o admin
                    notify_admin_new_lead(
                        lead["cnpj"],
                        lead["razao_social"],
                        lead["cidade"],
                        lead["uf"],
                        seg
                    )
                except Exception as e:
                    log_event("error", f"Failed to insert lead: {str(e)}")

                total += 1
            page_num = 1
        
        conn.commit()

    log_event(
        "capture",
        f"date={hoje} total={total} inserted={inserted} pages={page_num}",
    )


def queue_initial_messages_job():
    """Enfileira mensagens iniciais para leads do dia."""
    with get_conn() as conn:
        leads = conn.execute("""
            SELECT id, telefone FROM leads
            WHERE created_at >= datetime('now', '-1 day')
            AND id NOT IN (SELECT lead_id FROM messages)
        """).fetchall()

        for lead in leads:
            conn.execute("""
                INSERT INTO messages(lead_id, kind, template_key, message_text, status)
                VALUES (?, ?, ?, ?, 'queued')
            """, (lead["id"], "first", "default", "Olá!"))

        log_event("queue", f"queued={len(leads)} messages")


def dispatch_messages_job():
    """Dispara mensagens enfileiradas (respeitando horário comercial)."""
    from utils import is_business_hours

    if not is_business_hours():
        return

    with get_conn() as conn:
        messages = conn.execute("""
            SELECT id, lead_id FROM messages
            WHERE status='queued'
            LIMIT 10
        """).fetchall()

        for msg in messages:
            conn.execute(
                "UPDATE messages SET status='sent', sent_at=? WHERE id=?",
                (datetime.utcnow().isoformat(), msg["id"]),
            )

        log_event("dispatch", f"sent={len(messages)}")


def schedule_followups_job():
    """Agenda mensagens de follow-up."""
    log_event("followup", "scheduled")
