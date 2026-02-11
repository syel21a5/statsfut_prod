# Guia: Como Clonar o Site para uma Nova Versão (Ex: statsfut3)

Este guia serve para quando você quer criar uma nova cópia do site (ex: `statsfut3`) a partir de uma pasta existente, sem enfrentar erros de permissão ou conflito de portas.

---

## 1. Copiar e Renomear a Pasta
Faça a cópia da pasta do projeto atual para a nova (ex: de `statsfut2` para `statsfut3`).
No gerenciador de arquivos, renomeie a pasta para o nome final desejado (ex: `statsfut3.statsfut.com` ou apenas `statsfut3`).

---

## 2. Limpeza do Ambiente Virtual (O PASSO MAIS IMPORTANTE)
Ao copiar a pasta, o Python antigo (`venv`) vem junto, mas ele contém os caminhos da pasta velha. Isso quebra tudo. **Você precisa recriá-lo.**

Abra o Terminal e rode:

```bash
# 1. Entre na NOVA pasta
cd /www/wwwroot/statsfut3  <-- AJUSTE O NOME AQUI

# 2. Apague o ambiente virtual antigo e logs velhos
rm -rf venv
rm -rf logs/*

# 3. Crie um novo ambiente virtual
python3 -m venv venv

# 4. Ative e instale as dependências
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn gevent gevent-websocket
```

---

## 3. Ajustar Permissões e Criar Logs
O Linux precisa saber que essa nova pasta pertence ao usuário do servidor web (`www`).

```bash
# Cria a pasta de logs (se não existir)
mkdir -p logs

# Ajusta o dono dos arquivos
chown -R www:www .
chmod -R 755 .
```

---

## 4. Configurar o Novo Projeto no Painel (Python Manager)

1.  **Adicione o Projeto:** Aponte para a nova pasta (`/www/wwwroot/statsfut3`).
2.  **Escolha uma NOVA Porta:**
    *   Se `statsfut2` usa **8082**
    *   E `statsfut` usa **8084**
    *   O `statsfut3` deve usar **8085** (ou outra livre). **Nunca repita a porta!**
3.  **Ajuste a Configuração (Gunicorn):**
    Copie a configuração de um site funcionando, mas mude estas 3 linhas:

    ```python
    bind = '0.0.0.0:8085'               # <--- NOVA PORTA
    chdir = '/www/wwwroot/statsfut3'    # <--- NOVO CAMINHO
    pidfile = chdir + '/logs/statsfut3.pid'
    ```

4.  **Arquivo de Configuração:**
    Se o servidor reclamar de extensão, garanta que o arquivo de configuração se chame `gunicorn_conf.py` (com **.py** no final).

---

## 5. Banco de Dados (.env)
Não esqueça de abrir o arquivo `.env` da nova pasta e mudar o nome do banco de dados (se você quiser um banco separado para o novo site).

```bash
nano .env
# Mude DB_NAME, DB_USER, etc.
```

---

## Resumo Rápido (Cheat Sheet)

```bash
cd /www/wwwroot/NOVA_PASTA
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn gevent gevent-websocket
mkdir -p logs
chown -R www:www .
```
