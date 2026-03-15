import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, Match, LeagueStanding, TeamGoalTiming, Goal, League

def force_clean():
    league = League.objects.filter(name__icontains='Brasil').first()
    if not league:
        return

    # Vamos garantir que não existe NENHUM time extra com o mesmo nome aproximado
    # Array de "verdadeiros" IDs
    true_teams = ["Atletico-MG", "Vasco", "Bragantino", "Athletico"]
    
    for tt_name in true_teams:
        tt = Team.objects.filter(name=tt_name, league=league).first()
        if not tt: continue
        
        # Procura por intrusos usando partes do nome
        if tt_name == "Atletico-MG":
            bad_teams = Team.objects.filter(name__icontains="Mineiro", league=league).exclude(id=tt.id)
        elif tt_name == "Bragantino":
            bad_teams = Team.objects.filter(name__icontains="Red Bull", league=league).exclude(id=tt.id)
        elif tt_name == "Vasco":
            bad_teams = Team.objects.filter(name__icontains="Vasco da Gama", league=league).exclude(id=tt.id)
        elif tt_name == "Athletico":
            bad_teams = Team.objects.filter(name__icontains="Paranaense", league=league).exclude(id=tt.id)
        
        for bad in bad_teams:
            print(f"Forçando exclusão do intruso '{bad.name}' (ID {bad.id}) a favor de '{tt.name}'")
            
            # Exclui jogos duplicados
            for m in Match.objects.filter(home_team=bad):
                if Match.objects.filter(home_team=tt, away_team=m.away_team, date=m.date).exists():
                    m.delete()
                else:
                    m.home_team = tt
                    m.save()
                    
            for m in Match.objects.filter(away_team=bad):
                if Match.objects.filter(home_team=m.home_team, away_team=tt, date=m.date).exists():
                    m.delete()
                else:
                    m.away_team = tt
                    m.save()
                    
            Goal.objects.filter(team=bad).update(team=tt)
            LeagueStanding.objects.filter(team=bad).delete()
            TeamGoalTiming.objects.filter(team=bad).delete()
            
            bad.delete()

    # Recalcula do zero
    print("Recalculando classificação final oficial...")
    from matches.management.commands.recalculate_standings import Command
    cmd = Command()
    cmd.handle(league_name=league.name, country=league.country, full=True)

    print("Limpeza finalizada com sucesso! Verifique a tabela de classificação.")

if __name__ == "__main__":
    force_clean()
