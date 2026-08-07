from django.test import TestCase, Client
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta
from matches.models import Match, League, Team


class HomepageTipOfTheDayTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Priority League: Brasileirão Série A
        self.league_br = League.objects.create(
            name="Brasileirão Série A",
            country="Brasil",
            api_id=10
        )
        
        # Priority League: Premier League
        self.league_pl = League.objects.create(
            name="Premier League",
            country="Inglaterra",
            api_id=11
        )
        
        # Other League
        self.league_other = League.objects.create(
            name="Test League",
            country="Test Country",
            api_id=12
        )

        self.team_a = Team.objects.create(name="Team A", api_id=201, league=self.league_br)
        self.team_b = Team.objects.create(name="Team B", api_id=202, league=self.league_br)
        self.team_c = Team.objects.create(name="Team C", api_id=203, league=self.league_pl)
        self.team_d = Team.objects.create(name="Team D", api_id=204, league=self.league_pl)
        self.team_e = Team.objects.create(name="Team E", api_id=205, league=self.league_other)
        self.team_f = Team.objects.create(name="Team F", api_id=206, league=self.league_other)

        # Base date is now
        self.base_date = timezone.now()

    def test_no_matches_no_tip(self):
        # When no matches are scheduled for today or tomorrow, tip_of_the_day should be None
        response = self.client.get(reverse('matches:home'))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['tip_of_the_day'])
        self.assertNotIn('Tip of the Day', response.content.decode('utf-8'))

    def test_br_league_priority(self):
        # Create a Premier League match and a Brasileirão Série A match
        # Brasileirão match should be selected due to higher priority
        match_pl = Match.objects.create(
            home_team=self.team_c,
            away_team=self.team_d,
            league=self.league_pl,
            date=self.base_date + timedelta(hours=5),
            status="Scheduled"
        )
        
        match_br = Match.objects.create(
            home_team=self.team_a,
            away_team=self.team_b,
            league=self.league_br,
            date=self.base_date + timedelta(hours=10),
            status="Scheduled"
        )
        
        response = self.client.get(reverse('matches:home'))
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context['tip_of_the_day'])
        self.assertEqual(response.context['tip_of_the_day']['match'], match_br)
        
        html = response.content.decode('utf-8')
        self.assertIn('Tip of the Day', html)
        self.assertIn('Team A', html)
        self.assertIn('Team B', html)
