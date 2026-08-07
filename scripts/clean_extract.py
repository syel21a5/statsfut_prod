import os
import shutil
import zipfile

def clean_extract():
    zip_path = "/www/wwwroot/statsfut.com/local_logos_backup.zip"
    extract_dir = "/www/wwwroot/statsfut.com/static/teams/"

    if not os.path.exists(zip_path):
        print(f"ERRO: Arquivo ZIP não encontrado em {zip_path}")
        return

    print("Destruindo lixo anterior...")
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
        print(" -> Pasta /static/teams/ removida da existência.")

    print("Extraindo APENAS as imagens perfeitas...")
    os.makedirs(extract_dir, exist_ok=True)

    extracted_count: int = 0
    with zipfile.ZipFile(zip_path, 'r') as z:
        for info in z.infolist():
            # Pegamos o nome exato dentro do zip (ex: alemanha\bundesliga\sofa_123.png)
            filename = info.filename
            
            # 1. Ignorar pastas e focar só no que é imagem real
            if not filename.endswith('.png'):
                continue
                
            # 2. Ignorar lixo oculto do Mac/Windows
            if '__MACOSX' in filename or '/.' in filename or '\\.' in filename or filename.startswith('.'):
                continue
                
            # 3. Limpar nome e forçar barras corretas de Linux
            clean_name = filename.replace('\\', '/')
            
            # Se a barra inicial da pasta teams/ estiver lá, removemos para casar com o extract_dir
            if clean_name.startswith('static/teams/'):
                clean_name = clean_name.replace('static/teams/', '', 1)
            elif clean_name.startswith('teams/'):
                # Caso o zip tenha sido feito de dentro da pasta
                clean_name = clean_name.replace('teams/', '', 1)
                
            dest = os.path.join(extract_dir, clean_name)
            
            # Criar a pasta limpa se não existir
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            
            # Extrair o conteúdo bruto e salvar limpo
            with open(dest, 'wb') as f:
                f.write(z.read(filename))
                
            extracted_count = extracted_count + 1  # type: ignore[operator]

    print(f"-> SUCESSO ABSOLUTO! {extracted_count} imagens de logos extraídas.")
    print("Zero pastas fantasmas. Zero contra-barras malditas.")

if __name__ == '__main__':
    clean_extract()
