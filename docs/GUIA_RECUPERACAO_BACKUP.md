# Guia de Recuperação de Emergência (Backup/Zip)

Este guia serve para quando você **apaga a pasta do site** e **restaura um backup manual (arquivo .zip)**.

Quando fazemos isso, o Linux perde as configurações de "dono" dos arquivos e algumas pastas vazias essenciais. O site vai ficar fora do ar até corrigirmos isso.

## Sintomas
- O site dá "Erro 502 Bad Gateway" ou não carrega.
- O gerenciador de projetos Python mostra o status "Stopped" e não inicia.
- Os logs de erro dizem "Permission denied" ou "No such file or directory".

---

## Passo a Passo para Consertar

Siga estes passos na ordem exata usando o **Terminal** do servidor.

### 1. Acesse a pasta do projeto
Entre no diretório onde os arquivos foram descompactados.

```bash
cd /www/wwwroot/statsfut2.statsfut.com
```

### 2. Recrie a pasta de Logs (CRÍTICO)
O servidor (Gunicorn) **não inicia** se não tiver onde gravar os erros. Como pastas vazias geralmente não vão no Zip, ela deve ter sumido.

```bash
mkdir -p logs
```

### 3. Corrija as Permissões (CRÍTICO)
Quando você descompacta um Zip, os arquivos ficam pertencendo ao usuário `root`. Mas o site roda com o usuário `www`. Precisamos devolver os arquivos para ele.

```bash
# Define o dono como 'www' (usuário e grupo)
chown -R www:www .

# Garante permissões de leitura e execução corretas
chmod -R 755 .
```

### 4. Verifique o arquivo de senhas (.env)
Arquivos que começam com ponto (`.`) são ocultos e às vezes não entram no backup.
Verifique se ele existe:

```bash
ls -la .env
```

- **Se aparecer o arquivo:** Ótimo, pule para o passo 5.
- **Se der erro (não encontrado):** Você precisa recriá-lo.
    ```bash
    cp .env.example .env
    nano .env
    # (Cole suas configurações do banco de dados e salve com Ctrl+O, Enter, Ctrl+X)
    ```

### 5. Reinstale as Dependências (Opcional, mas recomendado)
Se a pasta `venv` (Ambiente Virtual) foi apagada ou corrompida, o Python não vai achar o Django.

```bash
# Ativa o ambiente virtual
source venv/bin/activate

# Instala tudo que está no requirements.txt
pip install -r requirements.txt
```

### 6. Reinicie o Site
Agora vá no painel de controle do seu servidor (Python Manager) e clique em **Start** ou **Restart**.

---

## Resumo dos Comandos (Para copiar e colar)

Se você já sabe que o `.env` e o `venv` estão ok, rode apenas isso para consertar logs e permissões:

```bash
cd /www/wwwroot/statsfut2.statsfut.com
mkdir -p logs
chown -R www:www .
chmod -R 755 .
```
