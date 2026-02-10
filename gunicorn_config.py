workers = 3
bind = "0.0.0.0:8000"
# Caminho para o log de erro - ajuste conforme necessário no servidor
errorlog = "/www/wwwroot/statsfut.com/gunicorn_error.log"
# Nível de log
loglevel = "info"
# Timeout para evitar que workers morram em requests longos
timeout = 120
# Nome do processo para facilitar identificação
proc_name = "statsfut_gunicorn"
