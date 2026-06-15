# Skill 14: Como Criar e Conectar Robôs do Telegram (Alertas Ao Vivo)

Esta skill ensina a arquitetura exata de como criamos o **Radar StatsFut Ao Vivo**, para que você possa replicar essa inteligência e criar dezenas de outros robôs (Ex: Robô de Escanteios, Robô de Ambas Marcam, Robô de Alertas VIP) no futuro.

---

## 🛠️ Passo 1: O "Nascimento" do Robô (BotFather)
O Telegram fornece uma API oficial e 100% gratuita para desenvolvedores. Você não precisa de servidores externos para criar o robô no Telegram, basta falar com o **@BotFather**.

1. Abra o Telegram e busque por `@BotFather`.
2. Envie o comando `/newbot`.
3. Dê um nome legível (Ex: `Robô de Escanteios`).
4. Dê um *username* obrigatório que termine em "bot" (Ex: `StatsFutCorners_bot`).
5. O BotFather vai te dar um **Token HTTP API** (ex: `123456789:ABCdefGHIjklmNOPQrsTUVwxyZ`). Guarde-o com a sua vida.

---

## ⚙️ Passo 2: Configurando o Servidor Django
Para o sistema falar com o robô, precisamos guardar a chave mágica (Token) no `core/settings.py` e criar a variável do `Chat ID` (o número que identifica quem vai receber a mensagem - você ou o seu Grupo VIP).

Adicione no `settings.py`:
```python
# Configuração do Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'SEU_TOKEN_AQUI')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', 'SEU_CHAT_ID_AQUI')
```

---

## 📡 Passo 3: O Motor de Disparo (`telegram_bot.py`)
Criamos um arquivo de serviço (`matches/services/telegram_bot.py`) genérico. Ele é o carteiro. A única função dele é pegar um Texto e entregar pro Telegram.

```python
import requests
import logging
from django.conf import settings

class TelegramBotService:
    @staticmethod
    def send_message(text: str, chat_id: str = None) -> bool:
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        target_chat_id = chat_id or getattr(settings, 'TELEGRAM_CHAT_ID', None)
        
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": target_chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        requests.post(url, json=payload)
```
**Dica Pro:** Usando `"parse_mode": "HTML"`, você pode enviar textos em negrito `<b>`, itálico `<i>` e com Emojis normais no texto!

---

## 🧠 Passo 4: Como Descobrir o seu Chat ID?
Para o robô saber pra onde mandar, você precisa do ID. 
1. Mande um "Oi" para o seu robô no Telegram.
2. Vá no navegador e acesse: `https://api.telegram.org/bot<SEU_TOKEN>/getUpdates`
3. Procure por `"chat":{"id": 12345678}`. Esse é o seu ID.

---

## 🎯 Passo 5: O Cérebro da Operação (Regras de Negócio)
Aqui é onde o Trader Esportivo trabalha. O Carteiro (Passo 3) já existe, agora precisamos de um Detetive para saber *quando* escrever a carta.

Criamos o `live_lay_detector.py` (ou `corner_detector.py`). A estrutura é sempre a mesma:
1. **Busca na base:** Traz do MySQL todos os jogos ao vivo (`Match.objects.filter(status='2H')`).
2. **Aplicar Filtros Matemáticos:** Analisar o tempo de jogo (`elapsed_time`), gols, cartões vermelhos.
3. **Decisão:** Se a regra de ouro bater (Ex: Lay tem 96% de chance e está na Janela de 15' a 65' minutos), montar a mensagem.
4. **Evitar Spam (Crucial):** Salvar em Cache que a mensagem já foi enviada para não metralhar o celular do usuário a cada minuto.
5. **Disparo:** Chamar `TelegramBotService.send_message(texto)`.

---

## ⏰ Passo 6: O Vigia Noturno (Cronjob)
Para o detetive trabalhar sozinho, amarramos ele num Command do Django (`run_live_lay_bot.py`) e colocamos no arquivo infinito de `schedule` (`run_live_updates.py`).

```python
import schedule

def job_robo_telegram():
    subprocess.run(["python", "manage.py", "run_live_lay_bot"])

# Rodar de 2 em 2 minutos! (Custo Zero de API, pois só acessa banco local)
schedule.every(2).minutes.do(job_robo_telegram)
```

### 🏆 Conclusão
Com esses 6 passos, você pode replicar esse sistema infinitamente! Pode criar o "Robô de Zebras", o "Robô de Gols no Fim (Over 0.5 FT)", e por aí vai. É só mudar as regras matemáticas do Passo 5!
