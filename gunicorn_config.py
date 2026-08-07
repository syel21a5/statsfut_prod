workers = 3
bind = "0.0.0.0:8092"

# ── Logging ──────────────────────────────────────────────
errorlog = "/www/wwwroot/statsfut.com/logs/gunicorn_error.log"
accesslog = "/www/wwwroot/statsfut.com/logs/gunicorn_access.log"
loglevel = "info"
capture_output = True  # Captura print() e tracebacks do Django no errorlog

# ── Timeout & Graceful Restart ───────────────────────────
timeout = 120          # Mata worker que demorar mais de 120s em 1 request
graceful_timeout = 30  # Tempo para worker terminar requests pendentes ao reiniciar

# ── Auto-reciclar workers (PREVINE MEMORY LEAK) ─────────
max_requests = 1000         # Reinicia cada worker a cada 1000 requests
max_requests_jitter = 100   # Variação aleatória para não reiniciar todos juntos

# ── Identificação ───────────────────────────────────────
proc_name = "statsfut_gunicorn"

# ── Performance ─────────────────────────────────────────
preload_app = True  # Carrega o app uma vez e faz fork (usa menos memória)
