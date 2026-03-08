import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League, Team, Match, LeagueStanding

TEAM_MAPPING = {
    "SK Sturm Graz": "Sturm Graz",
    "Salzburg": "Red Bull Salzburg",
    "FK Austria Wien": "Austria Vienna",
    "SK Rapid Wien": "Rapid Vienna",
    "Grazer AK 1902": "GAK 1902",
    "FC Blau Weiß Linz": "Blau-Weiss Linz",
    "WSG Tirol": "WSG Tirol",
    "SC Rheindorf Altach": "SC Rheindorf Altach",
    "Wolfsberger AC": "Wolfsberger AC",
    "TSV Hartberg": "TSV Hartberg",
    "LASK": "LASK",
    "SV Ried": "SV Ried",
}

def fix_duplicates():
    print('--- CORRIGINDO TIMES DUPLICADOS DO SOFASCORE ---')
    league = League.objects.filter(country='Austria').first()
    if not league:
        print('Liga da Áustria não encontrada.')
        return

    for sofa_name, canonical_name in TEAM_MAPPING.items():
        if sofa_name == canonical_name:
            continue
            
        # Busca o time criado pelo SofaScore (com nome incorreto e api_id)
        team_sofa = Team.objects.filter(league=league, name=sofa_name).first()
        
        # Busca o time canônico criado pelo histórico
        team_canonical = Team.objects.filter(league=league, name=canonical_name).first()

        if team_sofa and team_canonical and team_sofa.id != team_canonical.id:
            print(f'➜ Mesclando: "{team_sofa.name}" para "{team_canonical.name}"')
            
            # Limpa o api_id do time duplicado antes de deletar, para evitar conflito de unique
            # O time canônico já tem o api_id correto de uma importação anterior
            if team_sofa.api_id:
                team_sofa.api_id = None
                team_sofa.save()

            # Transferir partidas (Home)
            matches_home = Match.objects.filter(home_team=team_sofa)
            count_h = matches_home.update(home_team=team_canonical)
            
            # Transferir partidas (Away)
            matches_away = Match.objects.filter(away_team=team_sofa)
            count_a = matches_away.update(away_team=team_canonical)
            
            # Deletar classificações do time antigo (sofascore) para evitar duplicação na tabela
            LeagueStanding.objects.filter(team=team_sofa).delete()
            
            # Deletar o time duplicado
            team_sofa.delete()
            
            print(f'   ✅ {count_h} partidas mandante e {count_a} visitante movidas. Time "{sofa_name}" apagado.')

    # Recalcula a tabela para a temporada atual
    from django.core.management import call_command
    print('\nRecalculando a tabela da temporada 2024/2025...')
    call_command("recalculate_standings", league_name=league.name, country=league.country, season_year=2025)
    print('Tudo pronto! Seu banco de dados está uniforme.')

if __name__ == '__main__':
    fix_duplicates()
