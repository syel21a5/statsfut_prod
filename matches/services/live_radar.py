import logging
from datetime import timedelta
from django.utils import timezone
from django.db.models import F
from matches.models import Match, LiveMatchSnapshot

logger = logging.getLogger(__name__)

class LiveRadarService:
    """
    Serviço responsável por tirar 'fotografias' dos jogos ao vivo a cada X minutos
    e calcular a métrica de Pressão (Attack Momentum).
    """

    @staticmethod
    def take_snapshots_for_active_matches():
        """
        Busca todos os jogos ao vivo e salva os stats atuais em um LiveMatchSnapshot.
        Deve ser rodado por um CronJob a cada 1 ou 5 minutos.
        """
        # Apenas jogos que estão acontecendo agora
        active_matches = Match.objects.filter(status__in=['Live', 'Halftime', '1H', '2H', 'HT', 'ET', 'P', 'In Play', 'IN_PLAY', 'PAUSED'])
        
        snapshots_created = 0
        for match in active_matches:
            # Pega o minuto atual (elapsed_time do campo do Match)
            try:
                minute = int(match.elapsed_time) if match.elapsed_time else 0
            except (ValueError, TypeError):
                minute = 0
                
            # Salva a fotografia do momento
            LiveMatchSnapshot.objects.create(
                match=match,
                minute=minute,
                home_shots_on_target=match.home_shots_on_target or 0,
                away_shots_on_target=match.away_shots_on_target or 0,
                home_shots_off_target=getattr(match, 'home_shots_off_target', 0),
                away_shots_off_target=getattr(match, 'away_shots_off_target', 0),
                home_corners=match.home_corners or 0,
                away_corners=match.away_corners or 0,
                home_dangerous_attacks=getattr(match, 'home_dangerous_attacks', 0),
                away_dangerous_attacks=getattr(match, 'away_dangerous_attacks', 0),
                home_possession=match.home_possession or 50,
                away_possession=match.away_possession or 50
            )
            snapshots_created += 1
            
        logger.info(f"[LiveRadar] Tirou {snapshots_created} snapshots de jogos ao vivo.")
        return snapshots_created

    @staticmethod
    def calculate_pressure(match, window_minutes=5):
        """
        Calcula a pressão dos últimos X minutos usando o Snapshot antigo.
        Retorna um dicionário com a porcentagem de pressão (Casa vs Fora).
        """
        # Pega as estatísticas atuais do jogo (Momento T0)
        current_stats = {
            'home_shots': match.home_shots or 0,
            'away_shots': match.away_shots or 0,
            'home_da': getattr(match, 'home_dangerous_attacks', 0),
            'away_da': getattr(match, 'away_dangerous_attacks', 0),
            'home_corners': match.home_corners or 0,
            'away_corners': match.away_corners or 0
        }
        
        # Pega o snapshot salvo há X minutos atrás (Momento T-X)
        time_threshold = timezone.now() - timedelta(minutes=window_minutes)
        # Pega o snapshot mais próximo desse tempo limite, mas que seja ANTES do limite
        old_snapshot = LiveMatchSnapshot.objects.filter(
            match=match, 
            timestamp__lte=time_threshold
        ).first()
        
        if not old_snapshot:
            # Se não tem histórico antigo o suficiente, usa o T0 (ou seja, desde o início do jogo)
            # Para não quebrar a lógica, assumimos que as estatísticas passadas eram 0
            old_stats = {k: 0 for k in current_stats}
        else:
            old_stats = {
                'home_shots': old_snapshot.home_shots_on_target + old_snapshot.home_shots_off_target,
                'away_shots': old_snapshot.away_shots_on_target + old_snapshot.away_shots_off_target,
                'home_da': old_snapshot.home_dangerous_attacks,
                'away_da': old_snapshot.away_dangerous_attacks,
                'home_corners': old_snapshot.home_corners,
                'away_corners': old_snapshot.away_corners
            }
            
        # Calcula a diferença (O que aconteceu apenas nessa janela de tempo)
        diff = {
            'home_shots': max(0, current_stats['home_shots'] - old_stats['home_shots']),
            'away_shots': max(0, current_stats['away_shots'] - old_stats['away_shots']),
            'home_da': max(0, current_stats['home_da'] - old_stats['home_da']),
            'away_da': max(0, current_stats['away_da'] - old_stats['away_da']),
            'home_corners': max(0, current_stats['home_corners'] - old_stats['home_corners']),
            'away_corners': max(0, current_stats['away_corners'] - old_stats['away_corners']),
        }
        
        # Nossa Fórmula de Inteligência (Peso de cada ação)
        # Chutes = Peso 3, Escanteios = Peso 2, Ataques Perigosos = Peso 1
        home_score = (diff['home_shots'] * 3) + (diff['home_corners'] * 2) + (diff['home_da'] * 1)
        away_score = (diff['away_shots'] * 3) + (diff['away_corners'] * 2) + (diff['away_da'] * 1)
        
        total_score = home_score + away_score
        
        if total_score == 0:
            return {'home_pressure': 50, 'away_pressure': 50, 'status': 'Jogo Parado'}
            
        home_pressure = int((home_score / total_score) * 100)
        away_pressure = 100 - home_pressure
        
        return {
            'home_pressure': home_pressure,
            'away_pressure': away_pressure,
            'status': 'Casa Dominando' if home_pressure > 60 else 'Fora Dominando' if away_pressure > 60 else 'Equilibrado'
        }
