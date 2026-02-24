import os
import requests
import sys

def load_env_file():
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    keys = {}
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    k, v = line.split('=', 1)
                    keys[k.strip()] = v.strip()
    return keys

def test_keys():
    try:
        env_vars = load_env_file()
        
        output = []
        output.append("🔍 Iniciando teste de chaves da The Odds API...\n")
        
        # Filtrar chaves relevantes
        api_keys = {k: v for k, v in env_vars.items() if k.startswith('ODDS_API_KEY_')}
        
        if not api_keys:
            output.append("❌ Nenhuma chave ODDS_API_KEY_ encontrada no arquivo .env")
        
        for key_name, key_value in api_keys.items():
            masked_key = key_value[:4] + "..." + key_value[-4:]
            url = f"https://api.the-odds-api.com/v4/sports/?apiKey={key_value}"
            
            try:
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    headers = response.headers
                    rem = headers.get('x-requests-remaining', 'N/A')
                    used = headers.get('x-requests-used', 'N/A')
                    output.append(f"✅ {key_name}: OK")
                    output.append(f"   🔑 Key: {masked_key}")
                    output.append(f"   📊 Créditos: Usados {used} | Restantes {rem}")
                else:
                    output.append(f"❌ {key_name}: FALHA (Status {response.status_code})")
                    output.append(f"   🔑 Key: {masked_key}")
                    try:
                        msg = response.json().get('message', 'Erro desconhecido')
                        output.append(f"   ⚠️  Erro: {msg}")
                    except:
                        output.append(f"   ⚠️  Erro: {response.text[:100]}")
                        
            except Exception as e:
                output.append(f"❌ {key_name}: Erro de Conexão")
                output.append(f"   ⚠️  {str(e)}")
                
            output.append("-" * 60)
            
        # Escrever tudo no arquivo de uma vez
        with open('test_keys_output.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(output))
            
    except Exception as e:
        with open('test_keys_output.txt', 'w', encoding='utf-8') as f:
            f.write(f"ERRO CRÍTICO NO SCRIPT: {str(e)}")

if __name__ == "__main__":
    test_keys()
