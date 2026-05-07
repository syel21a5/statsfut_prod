import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import LeagueStanding, League, Season, Team

def run():
    bel = League.objects.get(id=10)
    sea = Season.objects.filter(matches__league=bel).order_by('-year').first()
    
    # Delete old standings for Belgium
    LeagueStanding.objects.filter(league=bel, season=sea).delete()

    teams_map = {
        'usg': 2527,
        'brugge': 2516,
        'truidense': 2504,
        'gent': 2505,
        'mechelen': 2533,
        'anderlecht': 1867,
        'genk': 1862,
        'standard': 1864,
        'westerlo': 2510,
        'antwerp': 1859,
        'charleroi': 2508,
        'leuven': 2543,
        'zulte': 2094,
        'cercle': 2513,
        'louviere': 2503,
        'dender': 2528
    }

    def create_standing(group, pos, team_key, p, w, d, l, gf, ga, pts):
        team_id = teams_map[team_key]
        team = Team.objects.get(id=team_id)
        LeagueStanding.objects.create(
            league=bel,
            season=sea,
            team=team,
            group_name=group,
            position=pos,
            played=p,
            won=w,
            drawn=d,
            lost=l,
            goals_for=gf,
            goals_against=ga,
            points=pts
        )

    # Regular Season
    g = 'Regular Season'
    create_standing(g, 1, 'usg', 30, 19, 9, 2, 50, 17, 66)
    create_standing(g, 2, 'brugge', 30, 20, 3, 7, 59, 36, 63)
    create_standing(g, 3, 'truidense', 30, 18, 3, 9, 47, 35, 57)
    create_standing(g, 4, 'gent', 30, 13, 6, 11, 49, 43, 45)
    create_standing(g, 5, 'mechelen', 30, 12, 9, 9, 39, 37, 45)
    create_standing(g, 6, 'anderlecht', 30, 12, 8, 10, 43, 39, 44)
    create_standing(g, 7, 'genk', 30, 11, 9, 10, 46, 47, 42)
    create_standing(g, 8, 'standard', 30, 11, 7, 12, 27, 35, 40)
    create_standing(g, 9, 'westerlo', 30, 10, 9, 11, 36, 40, 39)
    create_standing(g, 10, 'antwerp', 30, 9, 8, 13, 31, 32, 35)
    create_standing(g, 11, 'charleroi', 30, 9, 7, 14, 38, 42, 34)
    create_standing(g, 12, 'leuven', 30, 9, 7, 14, 32, 43, 34)
    create_standing(g, 13, 'zulte', 30, 8, 8, 14, 38, 47, 32)
    create_standing(g, 14, 'cercle', 30, 7, 10, 13, 39, 47, 31)
    create_standing(g, 15, 'louviere', 30, 6, 13, 11, 30, 37, 31)
    create_standing(g, 16, 'dender', 30, 3, 10, 17, 24, 51, 19)

    # Championship Round
    g = 'Championship Round'
    create_standing(g, 1, 'brugge', 36, 25, 3, 8, 77, 43, 47)
    create_standing(g, 2, 'usg', 36, 23, 10, 3, 58, 21, 46)
    create_standing(g, 3, 'truidense', 36, 21, 4, 11, 56, 40, 39)
    create_standing(g, 4, 'anderlecht', 36, 14, 8, 14, 52, 53, 28)
    create_standing(g, 5, 'mechelen', 36, 13, 10, 13, 44, 51, 27)
    create_standing(g, 6, 'gent', 36, 13, 9, 14, 51, 50, 26)

    # Relegation Round
    g = 'Relegation Round'
    create_standing(g, 1, 'zulte', 35, 12, 9, 14, 51, 52, 45)
    create_standing(g, 2, 'cercle', 35, 10, 11, 14, 52, 54, 41)
    create_standing(g, 3, 'louviere', 35, 6, 13, 16, 31, 49, 31)
    create_standing(g, 4, 'dender', 35, 5, 10, 20, 30, 60, 25)

    # Qualifying Round
    g = 'Qualifying Round'
    create_standing(g, 1, 'standard', 36, 14, 8, 14, 40, 42, 30)
    create_standing(g, 2, 'genk', 36, 13, 12, 11, 52, 53, 30)
    create_standing(g, 3, 'westerlo', 36, 13, 10, 13, 48, 50, 30)
    create_standing(g, 4, 'charleroi', 36, 12, 8, 16, 46, 48, 27)
    create_standing(g, 5, 'antwerp', 36, 12, 8, 16, 41, 44, 27)
    create_standing(g, 6, 'leuven', 36, 9, 9, 18, 36, 55, 19)

    print("Success! Created all 4 groups with exact data from screenshots.")

if __name__ == '__main__':
    run()
