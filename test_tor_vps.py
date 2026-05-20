import sys
import time

try:
    from curl_cffi import requests
    print("curl_cffi importado com sucesso!")
except ImportError:
    import requests
    print("requests importado com sucesso!")

import sys
import time

try:
    from curl_cffi import requests
    print("curl_cffi importado com sucesso!")
except ImportError:
    import requests
    print("requests importado com sucesso!")

def test_tor():
    test_url = "https://api.ipify.org?format=json"
    sofascore_url = "https://web-api.sofascore.com/api/v1/unique-tournament/17/season/76986/events/last/0"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://www.sofascore.com",
        "Referer": "https://www.sofascore.com/"
    }

    print("\n--- INICIANDO TESTE DE CONECTIVIDADE ---")

    # 1. Testar Acesso Direto (Sem Proxy)
    print("\n[TESTE 1] Acessando SofaScore DIRETAMENTE (Sem Proxy)...")
    try:
        start_time = time.time()
        direct_resp = requests.get(sofascore_url, headers=headers, timeout=10)
        elapsed = time.time() - start_time
        if direct_resp.status_code == 200:
            print(f"✅ Conexão Direta OK! Respondido em {elapsed:.2f}s")
        else:
            print(f"❌ Conexão Direta retornou status: {direct_resp.status_code}")
    except Exception as e:
        print(f"❌ Erro na Conexão Direta: {e}")

    # 2. Testar Tor Socks5h
    proxies = {"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"}
    print(f"\n[TESTE 2] Acessando via Tor (socks5h://127.0.0.1:9050)...")
    
    # Teste de IP básico
    try:
        ip_resp = requests.get(test_url, proxies=proxies, timeout=10)
        if ip_resp.status_code == 200:
            print(f"✅ Tor IP básico OK! IP do Tor: {ip_resp.json().get('ip')}")
        else:
            print(f"❌ Falha ao obter IP básico via Tor (Status: {ip_resp.status_code})")
    except Exception as e:
        print(f"❌ Erro ao conectar no Tor para IP básico: {e}")
        print("\n⚠️ O serviço do Tor não está respondendo localmente ou está bloqueado.")
        return False

    # Teste SofaScore com retentativas (forçando rotação de circuitos se falhar)
    print("\nTestando acesso ao SofaScore via Tor (fazendo 3 tentativas)...")
    for attempt in range(1, 4):
        print(f"Tentativa {attempt} de 3...")
        try:
            sofa_resp = requests.get(sofascore_url, proxies=proxies, headers=headers, timeout=15)
            if sofa_resp.status_code == 200:
                print("✅ Acesso ao SofaScore via Tor funcionou com sucesso!")
                print("\n🎉 O TOR ESTÁ 100% OPERACIONAL PARA ATUALIZAR O SOFASCORE!")
                return True
            else:
                print(f"❌ Tentativa {attempt} retornou status: {sofa_resp.status_code}")
        except Exception as e:
            print(f"❌ Tentativa {attempt} falhou: {e}")
            if attempt < 3:
                print("Reiniciando circuito do Tor para tentar com outro IP...")
                # Recarregar o serviço do Tor no Linux faz ele forçar uma rotação de IPs/Circuitos
                print("Aguardando 5 segundos antes de tentar novamente...")
                time.sleep(5)
                
    print("\n⚠️ O Tor está navegando na internet, mas o SofaScore está inacessível através dele.")
    print("Isso geralmente significa que a rede SofaScore/Cloudflare está bloqueando os Exit Nodes atuais do Tor.")
    print("Dica: Você pode recarregar o Tor na VPS para forçar novos IPs limpos com: 'sudo systemctl reload tor'")
    return False

if __name__ == "__main__":
    test_tor()
