from matches.models import Team

def fix_teams():
    print("Corrigindo Flandria...")
    Team.objects.filter(name__iexact='CSD Flandria').update(api_id='sofa_112505')
    
    print("Corrigindo Athletic Club...")
    Team.objects.filter(name__iexact='Athletic Club', league__name__icontains='Série B').update(api_id='sofa_342775')
    
    print("Corrigindo Santos...")
    # O banco de dados exige que o api_id seja único. 
    # Existem 3 'Santos' (Série A, Série B, Sul-Americana).
    santos_teams = list(Team.objects.filter(name__iexact='Santos'))
    
    # 1. Limpar todos para evitar conflito de chave única
    for t in santos_teams:
        t.api_id = None
        t.save()
        
    # 2. Setar o ID correto no primeiro (os outros usarão a lógica de duplicatas)
    if santos_teams:
        principal = santos_teams[0]
        principal.api_id = 'sofa_1968'
        principal.save()
    
    print("Feito! Limpe o cache.")

fix_teams()
