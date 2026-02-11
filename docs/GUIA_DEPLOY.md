# Guia de Desenvolvimento e Deploy - StatsFut

Este guia descreve o passo a passo para atualizar o site, desde a edição no seu computador até a publicação no servidor.

## 1. Fluxo de Trabalho (Dia a Dia)

O processo padrão para fazer alterações é sempre **editar localmente** e depois **enviar para o servidor**. Evite editar arquivos diretamente no servidor.

### Passo 1: No seu Computador (Local)
1.  Faça as alterações no código (VS Code, etc).
2.  Teste se possível.
3.  Envie as alterações para o GitHub:
    ```bash
    git add .
    git commit -m "Descrição do que foi alterado"
    git push origin main
    ```

### Passo 2: No Servidor (Deploy)
1.  Acesse o terminal do servidor (via SSH ou painel da hospedagem).
2.  Entre na pasta do projeto:
    ```bash
    cd /www/wwwroot/statsfut2.statsfut.com
    ```
3.  Baixe as atualizações:
    ```bash
    git pull origin main
    ```
4.  Reinicie o serviço (para aplicar alterações em arquivos Python/Django):
    *   **Encontre o processo:** `ps -ef | grep python` (procure pelo Gunicorn master)
    *   **Reinicie:** `kill -HUP <PID>` (substitua <PID> pelo número do processo)

---

## 2. Solução de Problemas (Quando o Deploy Falha)

Se ao tentar fazer o `git pull` você receber um erro dizendo que há alterações locais ou conflitos (ex: *"Your local changes to the following files would be overwritten by merge"*), siga estes passos.

**⚠️ CUIDADO:** Isso apagará qualquer alteração feita manualmente dentro do servidor e deixará ele idêntico ao GitHub.

1.  **Resetar o servidor para a versão do GitHub:**
    ```bash
    # Garante que o git conhece todas as novidades
    git fetch --all

    # Força o código local a ser IDÊNTICO ao do GitHub (apaga edições manuais do servidor)
    git reset --hard origin/main
    ```

2.  **Sincronizar:**
    ```bash
    git pull origin main
    ```

3.  **Reiniciar o serviço:**
    ```bash
    # Exemplo: se o PID for 102856
    kill -HUP 102856
    ```

## 3. Comandos Úteis no Servidor

*   **Verificar status do Git:** `git status`
*   **Verificar processos Python rodando:** `ps -ef | grep python`
*   **Ativar ambiente virtual (se necessário rodar scripts manuais):**
    ```bash
    source venv/bin/activate
    # ou o caminho específico do seu ambiente, caso seja diferente
    ```

---

## 4. Recuperação de Emergência (Caso apague arquivos ou restaure backup)

Se você apagou a pasta do servidor e restaurou um backup (zip), o site pode parar de funcionar pelos seguintes motivos:

1.  **Permissões incorretas:** O usuário do servidor (`www`) perdeu acesso aos arquivos.
2.  **Arquivos Ocultos:** O arquivo `.env` (configurações) geralmente não vai no zip.
3.  **Pasta de Logs:** O Gunicorn precisa da pasta `logs` para iniciar.
4.  **Ambiente Virtual:** As bibliotecas (Django, etc.) sumiram.

### Passo a Passo para Corrigir:

No terminal do servidor, execute:

1.  **Acesse a pasta:**
    ```bash
    cd /www/wwwroot/statsfut2.statsfut.com
    ```

2.  **Recrie a pasta de logs (essencial para o Gunicorn):**
    ```bash
    mkdir -p logs
    ```

3.  **Corrija as permissões (para usuário www):**
    ```bash
    chown -R www:www .
    chmod -R 755 .
    ```

4.  **Verifique se o arquivo .env existe:**
    ```bash
    ls -la .env
    ```
    *Se der erro dizendo que não existe, você precisará recriá-lo com suas senhas do banco de dados.*

5.  **Reinstale as dependências (se necessário):**
    Se usar o gerenciador de Python do painel, tente ir na aba "Module" e instalar o `requirements.txt` novamente.
    Ou via terminal:
    ```bash
    # Ative o ambiente virtual (ajuste o caminho se necessário)
    source venv/bin/activate  # ou source ../nome_do_venv/bin/activate
    pip install -r requirements.txt
    ```

6.  **Reinicie o Projeto no Painel.**

