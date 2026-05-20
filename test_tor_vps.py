import sys
import time

try:
    from curl_cffi import requests
    print("curl_cffi importado com sucesso!")
except ImportError:
    import requests
    print("requests importado com sucesso!")

def test_tor():
    # Testar na porta 9050 (padrão VPS/Linux) e também 9150 por precaução
    proxies_options = [
        {"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"},
        {"http": "socks5://127.0.0.1:9050", "https": "socks5://127.0.0.1:9050"},
        {"http": "socks5h://127.0.0.1:9150", "https": "socks5h://127.0.0.1:9150"},
    ]
    
    test_url = "https://api.ipify.org?format=json"
    # URL de teste do SofaScore (Premier League inglesa)
    sofascore_url = "https://web-api.sofascore.com/api/v1/unique-tournament/17/season/76986/events/last/0"
    
    print("\n--- INICIANDO TESTE DO TOR ---")
    
    for idx, proxies in enumerate(proxies_options):
        print(f"\nTentativa {idx + 1} usando proxy: {proxies['http']}")
        try:
            # Teste 1: Obter IP externo via Tor
            response = requests.get(test_url, proxies=proxies, timeout=15)
            if response.status_code == 200:
                print(f"✅ Conexão básica OK! IP retornado pelo Tor: {response.json().get('ip')}")
                
                # Teste 2: Acessar SofaScore via Tor
                print("Testando acesso à API do SofaScore...")
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                sofa_resp = requests.get(sofascore_url, proxies=proxies, headers=headers, timeout=15)
                if sofa_resp.status_code == 200:
                    print("✅ Acesso ao SofaScore OK! Dados recebidos com sucesso.")
                    print("\n🎉 O TOR ESTÁ FUNCIONANDO E CONECTADO COM SUCESSO!")
                    return True
                else:
                    print(f"❌ Falha ao acessar o SofaScore (Status: {sofa_resp.status_code})")
            else:
                print(f"❌ Falha na conexão básica (Status: {response.status_code})")
        except Exception as e:
            print(f"❌ Erro ao conectar usando este proxy: {e}")
            
    print("\n⚠️ O Tor não respondeu em nenhuma das portas testadas.")
    print("Dicas de Diagnóstico na VPS:")
    print("1. Verifique se o Tor está instalado: 'sudo apt install tor'")
    print("2. Verifique se o serviço está rodando: 'systemctl status tor'")
    print("3. Caso esteja parado, inicie-o: 'sudo systemctl start tor'")
    return False

if __name__ == "__main__":
    test_tor()
