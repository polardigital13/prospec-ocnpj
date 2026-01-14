import os
from dotenv import load_dotenv

load_dotenv()

import json
from datetime import datetime

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
    flash,
)
from apscheduler.schedulers.background import BackgroundScheduler

from database import init_db, get_conn, log_event
from scheduler_jobs import (
    capture_job,
    queue_initial_messages_job,
    dispatch_messages_job,
    schedule_followups_job,
)
from utils import to_e164_br

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev")


scheduler = None


def start_scheduler():
    """
    Inicia o APScheduler apenas uma vez.
    Importante: evitar rodar no processo "reloader" do Flask debug.
    """
    global scheduler
    if scheduler is not None:
        return scheduler

    sched = BackgroundScheduler(daemon=True)

    # Captura diária às 08:00
    sched.add_job(capture_job, "cron", hour=8, minute=0)

    # Enfileira mensagens logo após
    sched.add_job(queue_initial_messages_job, "cron", hour=8, minute=10)

    # Disparo frequente (o job respeita horário comercial)
    sched.add_job(dispatch_messages_job, "interval", minutes=2)

    # Follow-ups
    sched.add_job(schedule_followups_job, "interval", minutes=30)

    sched.start()
    scheduler = sched
    log_event("startup", "scheduler_started")
    return scheduler


def bootstrap():
    """
    Inicializa DB e Scheduler.
    Chamado no startup do app (não em request).
    """
    init_db()

    # Evita iniciar scheduler duplicado no debug reloader do Flask
    # - Quando debug=True, o Flask cria um processo "monitor" e outro que roda o app.
    # - Só queremos iniciar o scheduler no processo que realmente executa o app.
    if app.debug:
        if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
            start_scheduler()
    else:
        start_scheduler()

    log_event("startup", "app_bootstrapped")


@app.route("/")
def dashboard():
    with get_conn() as conn:
        total_leads = conn.execute("SELECT COUNT(*) c FROM leads").fetchone()["c"]
        total_sent = conn.execute(
            "SELECT COUNT(*) c FROM messages WHERE status='sent'"
        ).fetchone()["c"]
        total_failed = conn.execute(
            "SELECT COUNT(*) c FROM messages WHERE status='failed'"
        ).fetchone()["c"]
        optouts = conn.execute("SELECT COUNT(*) c FROM opt_out").fetchone()["c"]

        last_leads = conn.execute("""
            SELECT razao_social, cidade, uf, segmento, created_at, status
            FROM leads ORDER BY id DESC LIMIT 10
        """).fetchall()

        sent_7d = conn.execute("""
            SELECT substr(sent_at,1,10) as day, COUNT(*) as c
            FROM messages
            WHERE status='sent' AND sent_at IS NOT NULL
            GROUP BY day
            ORDER BY day DESC
            LIMIT 7
        """).fetchall()

    return render_template(
        "dashboard.html",
        total_leads=total_leads,
        total_sent=total_sent,
        total_failed=total_failed,
        optouts=optouts,
        last_leads=last_leads,
        sent_7d=list(reversed(sent_7d)),
    )


@app.route("/leads")
def leads():
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT id, cnpj, razao_social, cidade, uf, cnae_principal, telefone, email,
                   segmento, status, created_at
            FROM leads
            ORDER BY id DESC
            LIMIT 200
        """).fetchall()
    return render_template("leads.html", rows=rows)


@app.route("/reports")
def reports():
    with get_conn() as conn:
        by_segment = conn.execute("""
            SELECT segmento, COUNT(*) as leads
            FROM leads
            GROUP BY segmento
            ORDER BY leads DESC
        """).fetchall()

        by_template = conn.execute("""
            SELECT template_key, COUNT(*) as sent
            FROM messages
            WHERE status='sent'
            GROUP BY template_key
            ORDER BY sent DESC
        """).fetchall()

    return render_template("reports.html", by_segment=by_segment, by_template=by_template)


@app.route("/config", methods=["GET", "POST"])
def config():
    if request.method == "POST":
        templates_json = request.form.get("templates_json", "").strip()
        try:
            data = json.loads(templates_json)
            os.makedirs("message_templates", exist_ok=True)
            with open("message_templates/templates.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            flash("Templates atualizados com sucesso.", "success")
        except Exception as e:
            flash(f"Erro ao salvar templates: {e}", "danger")
        return redirect(url_for("config"))

    # Se não existir ainda, cria um arquivo vazio para evitar crash
    os.makedirs("message_templates", exist_ok=True)
    if not os.path.exists("message_templates/templates.json"):
        with open("message_templates/templates.json", "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)

    with open("message_templates/templates.json", "r", encoding="utf-8") as f:
        templates_json = f.read()

    env_view = {
        "CNAE_FILTRO": os.getenv("CNAE_FILTRO", ""),
        "UF_FILTRO": os.getenv("UF_FILTRO", ""),
        "LIMITE_DIARIO": os.getenv("LIMITE_DIARIO", "50"),
        "INTERVALO_ENVIO": os.getenv("INTERVALO_ENVIO", "30"),
        "HORA_INICIO": os.getenv("HORA_INICIO", "9"),
        "HORA_FIM": os.getenv("HORA_FIM", "18"),
    }
    return render_template("config.html", templates_json=templates_json, env_view=env_view)


@app.route("/optout", methods=["POST"])
def optout_admin():
    phone_raw = request.form.get("phone", "")
    phone = to_e164_br(phone_raw)
    if not phone:
        flash("Telefone inválido.", "danger")
        return redirect(url_for("config"))

    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO opt_out(phone, created_at, source) VALUES(?,?,?)",
            (phone, datetime.utcnow().isoformat(), "admin"),
        )
    flash("Número adicionado ao opt-out.", "success")
    return redirect(url_for("config"))


@app.route("/run/<job>")
def run_job(job):
    try:
        if job == "capture":
            capture_job()
        elif job == "queue":
            queue_initial_messages_job()
        elif job == "dispatch":
            dispatch_messages_job()
        elif job == "followups":
            schedule_followups_job()
        else:
            flash("Job inválido.", "warning")
            return redirect(url_for("dashboard"))

        flash(f"Job '{job}' executado.", "success")
    except Exception as e:
        flash(f"Erro ao executar job '{job}': {e}", "danger")
    return redirect(url_for("dashboard"))


@app.route("/api/metrics")
def api_metrics():
    with get_conn() as conn:
        leads_count = conn.execute("SELECT COUNT(*) c FROM leads").fetchone()["c"]
        sent_count = conn.execute(
            "SELECT COUNT(*) c FROM messages WHERE status='sent'"
        ).fetchone()["c"]
        failed_count = conn.execute(
            "SELECT COUNT(*) c FROM messages WHERE status='failed'"
        ).fetchone()["c"]
        optouts_count = conn.execute("SELECT COUNT(*) c FROM opt_out").fetchone()["c"]
        data = {
            "leads": leads_count,
            "sent": sent_count,
            "failed": failed_count,
            "optouts": optouts_count,
        }
    return jsonify(data)


@app.route("/webhook/zapi", methods=["POST"])
def webhook_zapi():
    payload = request.get_json(force=True, silent=True) or {}
    phone = payload.get("phone") or payload.get("from")
    text = (payload.get("text") or payload.get("message") or "").strip().upper()

    if phone:
        phone_e164 = to_e164_br(phone) or phone
        if "SAIR" in text:
            with get_conn() as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO opt_out(phone, created_at, source) VALUES(?,?,?)",
                    (phone_e164, datetime.utcnow().isoformat(), "webhook"),
                )
            log_event("optout", f"phone={phone_e164}")

    return jsonify({"ok": True})


@app.route("/health")
def health():
    with get_conn() as conn:
        last = conn.execute("SELECT * FROM events ORDER BY id DESC LIMIT 1").fetchone()
        last_event = dict(last) if last else None
    return jsonify({"ok": True, "last_event": last_event})


if __name__ == "__main__":
    # define debug via env ou padrão True em dev
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    app.debug = debug

    bootstrap()
    app.run(host="0.0.0.0", port=5000, debug=debug)
