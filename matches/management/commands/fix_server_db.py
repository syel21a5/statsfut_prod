from django.core.management.base import BaseCommand
from matches.models import League, Team, Match, LeagueStanding

class Command(BaseCommand):
    help = 'Fixes database inconsistencies (Mirassol, Athletic Club, and Serie A)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Iniciando correção do banco de dados..."))

        # 1. Corrigir ligas "Serie A" vazias
        self.stdout.write("\n--- 1. Corrigindo Serie A vs Brasileirão ---")
        brasileirao = League.objects.filter(name__iexact='Brasileirão', country__iexact='Brazil').first()
        if not brasileirao:
            brasileirao = League.objects.filter(name__iexact='Brasileirão', country__iexact='Brasil').first()

        if brasileirao:
            serie_a_leagues = League.objects.filter(name__iexact='Serie A', country__in=['Brazil', 'Brasil'])
            for sa in serie_a_leagues:
                if sa.matches.count() == 0:
                    self.stdout.write(f"Deletando liga Serie A (ID {sa.id}) pois está vazia.")
                    sa.delete()
                else:
                    self.stdout.write(f"Movendo {sa.matches.count()} jogos da Serie A (ID {sa.id}) para o Brasileirão.")
                    
                    # Para cada time na Serie A duplicada, precisamos ver se já existe no Brasileirão
                    # Se sim, transferimos os jogos. Se não, movemos o time.
                    for team in sa.teams.all():
                        br_team = Team.objects.filter(league=brasileirao, name__iexact=team.name).first()
                        if br_team:
                            # Time já existe no Brasileirão. Mover jogos e classificação para ele.
                            Match.objects.filter(home_team=team).update(home_team=br_team)
                            Match.objects.filter(away_team=team).update(away_team=br_team)
                            LeagueStanding.objects.filter(team=team).update(team=br_team)
                            team.delete()
                        else:
                            # Time não existe no Brasileirão. Apenas move a liga do time.
                            team.league = brasileirao
                            team.save()

                    # Agora que os times estão arrumados, atualiza a liga dos jogos e classificações
                    sa.matches.update(league=brasileirao)
                    LeagueStanding.objects.filter(league=sa).update(league=brasileirao)
                    sa.delete()
        else:
            self.stdout.write(self.style.ERROR("Erro: Liga Brasileirão não encontrada."))

        # 2. Corrigir Athletico-PR na Série B
        self.stdout.write("\n--- 2. Corrigindo Athletic Club vs Athletico-PR na Série B ---")
        serie_b = League.objects.filter(name__iexact='Série B', country__in=['Brazil', 'Brasil']).first()
        if serie_b:
            wrong_team = Team.objects.filter(league=serie_b, name__icontains='Athletico-PR').first()
            if wrong_team:
                self.stdout.write(f"Encontrado time errado na Série B: {wrong_team.name} (ID {wrong_team.id})")
                
                correct_team = Team.objects.filter(league=serie_b, name__icontains='Athletic Club').first()
                if not correct_team:
                    self.stdout.write("Criando o time correto 'Athletic Club' na Série B...")
                    correct_team = Team.objects.create(name='Athletic Club', league=serie_b, api_id='12257')
                
                self.stdout.write(f"Movendo jogos de {wrong_team.name} para {correct_team.name}...")
                Match.objects.filter(home_team=wrong_team).update(home_team=correct_team)
                Match.objects.filter(away_team=wrong_team).update(away_team=correct_team)
                LeagueStanding.objects.filter(team=wrong_team).update(team=correct_team)
                
                wrong_team.delete()
                self.stdout.write(self.style.SUCCESS("Time errado deletado com sucesso!"))
            else:
                self.stdout.write("Nenhum Athletico-PR encontrado na Série B. Tudo certo.")
        else:
            self.stdout.write(self.style.ERROR("Erro: Liga Série B não encontrada."))

        # 3. Corrigir Mirassol no Brasileirão
        self.stdout.write("\n--- 3. Unificando times do Mirassol no Brasileirão ---")
        if brasileirao:
            mirassol_teams = list(Team.objects.filter(league=brasileirao, name__icontains='Mirassol'))
            if len(mirassol_teams) > 1:
                self.stdout.write(f"Encontrados {len(mirassol_teams)} times do Mirassol no Brasileirão. Unificando...")
                
                main_team = None
                for t in mirassol_teams:
                    if LeagueStanding.objects.filter(team=t).exists():
                        main_team = t
                        break
                
                if not main_team:
                    main_team = mirassol_teams[0]

                self.stdout.write(f"Time principal escolhido: {main_team.name} (ID {main_team.id})")

                for t in mirassol_teams:
                    if t.id != main_team.id:
                        self.stdout.write(f"Movendo jogos de {t.name} (ID {t.id}) para o time principal...")
                        Match.objects.filter(home_team=t).update(home_team=main_team)
                        Match.objects.filter(away_team=t).update(away_team=main_team)
                        LeagueStanding.objects.filter(team=t).update(team=main_team)
                        t.delete()
                
                main_team.name = 'Mirassol'
                main_team.save()
                self.stdout.write(self.style.SUCCESS("Unificação do Mirassol concluída."))
            else:
                self.stdout.write("Não há Mirassol duplicado no Brasileirão. Tudo certo.")

        # 4. Corrigir erro de mapeamento Athletico-PR vs Atletico Goianiense no Brasileirão
        self.stdout.write("\n--- 4. Corrigindo API IDs de Athletico-PR e Atletico-GO ---")
        if brasileirao:
            wrong_goianiense = Team.objects.filter(league=brasileirao, api_id='134', name__icontains='Goianiense').first()
            if wrong_goianiense:
                # Procura se já existe o Atletico Goianiense correto (com ID 144)
                correct_goianiense = Team.objects.filter(api_id='144').first()
                if correct_goianiense:
                    self.stdout.write(f"Mesclando {wrong_goianiense.name} com o verdadeiro Atletico-GO (ID 144)...")
                    Match.objects.filter(home_team=wrong_goianiense).update(home_team=correct_goianiense)
                    Match.objects.filter(away_team=wrong_goianiense).update(away_team=correct_goianiense)
                    LeagueStanding.objects.filter(team=wrong_goianiense).update(team=correct_goianiense)
                    wrong_goianiense.delete()
                else:
                    wrong_goianiense.api_id = '144'
                    wrong_goianiense.save()
                self.stdout.write(self.style.SUCCESS("Corrigido API ID 134 do Atletico Goianiense."))
            
            correct_athletico = Team.objects.filter(league=brasileirao, name__icontains='Athletico-PR').first()
            if correct_athletico:
                if correct_athletico.api_id != '134':
                    correct_athletico.api_id = '134'
                    correct_athletico.save()
                    self.stdout.write(self.style.SUCCESS("Atribuído API ID 134 para o Athletico-PR."))
            
            # Deletar jogos duplicados criados com o mapeamento errado (Mirassol x Athletico-PR que virou Atletico-GO)
            deleted_count, _ = Match.objects.filter(api_id__in=['1492280', '1492477']).delete()
            if deleted_count > 0:
                self.stdout.write(self.style.SUCCESS(f"Deletados {deleted_count} jogos criados incorretamente (eles serão recriados/pareados corretamente na próxima sincronização)."))

        # 5. Limpar jogos duplicados (SofaScore vs API-Sports)
        self.stdout.write("\n--- 5. Limpando jogos duplicados do SofaScore ---")
        sofa_matches = Match.objects.filter(api_id__startswith='sofa_')
        deleted_sofa_count = 0
        for sm in sofa_matches:
            has_api_match = Match.objects.filter(
                home_team=sm.home_team,
                away_team=sm.away_team,
                season=sm.season,
                league=sm.league
            ).exclude(api_id__startswith='sofa_').exists()
            
            if has_api_match:
                sm.delete()
                deleted_sofa_count += 1
        
        if deleted_sofa_count > 0:
            self.stdout.write(self.style.SUCCESS(f"Deletados {deleted_sofa_count} jogos antigos do SofaScore que já possuíam versão atualizada da API."))
        else:
            self.stdout.write("Nenhum jogo duplicado do SofaScore encontrado.")

        self.stdout.write(self.style.SUCCESS("\n=== Todas as correções foram finalizadas! ==="))
