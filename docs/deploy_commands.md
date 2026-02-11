# 🚀 Deploy no Servidor - Comandos Rápidos

## 1️⃣ Atualizar código no servidor

```bash
cd /www/wwwroot/statsfut2.statsfut.com
git pull origin main
```

## 2️⃣ Instalar o serviço systemd

```bash
# Copiar arquivo de configuração
cp statsfut-live.service /etc/systemd/system/

# Recarregar systemd
systemctl daemon-reload

# Habilitar para iniciar no boot
systemctl enable statsfut-live.service

# Iniciar o serviço
systemctl start statsfut-live.service

# Verificar se está rodando
systemctl status statsfut-live.service
```

## 3️⃣ Monitorar logs

```bash
# Ver logs em tempo real
tail -f /www/wwwroot/statsfut2.statsfut.com/logs/live_updates.log
```

---

## 📊 O que esperar nos logs

```
🚀 StatsFut Smart Auto-Updater v2.0
📊 Configurações:
   • Modo ECONÔMICO: 300s (sem jogos)
   • Modo ATIVO: 60s (com jogos)
   • Sync Completo: 3600s (1 hora)
💡 Sistema inteligente: economiza ~80% de chamadas API!
```

---

## ⚙️ Comandos úteis

```bash
# Ver status
systemctl status statsfut-live

# Reiniciar
systemctl restart statsfut-live

# Parar
systemctl stop statsfut-live

# Ver logs de erro
tail -f /www/wwwroot/statsfut2.statsfut.com/logs/live_updates_error.log
```
