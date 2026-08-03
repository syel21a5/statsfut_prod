from django.test import TestCase, Client
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta
from matches.models import Match, League, Team

class MatchDetailRetentionModulesTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.league = League.objects.create(
            name="Test League",
            country="Test Country",
            api_id=1
        )
        self.team_a = Team.objects.create(name="Team A", api_id=101, league=self.league)
        self.team_b = Team.objects.create(name="Team B", api_id=102, league=self.league)
        self.team_c = Team.objects.create(name="Team C", api_id=103, league=self.league)
        self.team_d = Team.objects.create(name="Team D", api_id=104, league=self.league)
        
        base_date = timezone.now()
        # Base Match (Current)
        self.base_match = Match.objects.create(
            home_team=self.team_a,
            away_team=self.team_b,
            league=self.league,
            date=base_date,
            status="Scheduled"
        )
        
        # Next Match for Home Team (Team A)
        self.next_home = Match.objects.create(
            home_team=self.team_a,
            away_team=self.team_c,
            league=self.league,
            date=base_date + timedelta(days=2),
            status="Scheduled"
        )
        
        # Next Match for Away Team (Team B)
        self.next_away = Match.objects.create(
            home_team=self.team_d,
            away_team=self.team_b,
            league=self.league,
            date=base_date + timedelta(days=3),
            status="Scheduled"
        )
        
        # Other Match in the same round (League, +- 3 days, excluding current)
        self.other_round = Match.objects.create(
            home_team=self.team_c,
            away_team=self.team_d,
            league=self.league,
            date=base_date - timedelta(days=1),
            status="Scheduled"
        )

    def test_retention_modules_in_context(self):
        url = reverse('matches:match_detail', kwargs={'pk': self.base_match.pk, 'slug': self.base_match.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Check context
        self.assertIn('next_matches_home', response.context)
        self.assertIn('next_matches_away', response.context)
        self.assertIn('other_round_matches', response.context)
        
        next_home_list = list(response.context['next_matches_home'])
        next_away_list = list(response.context['next_matches_away'])
        other_round_list = list(response.context['other_round_matches'])
        
        self.assertEqual(len(next_home_list), 1)
        self.assertEqual(next_home_list[0], self.next_home)
        
        self.assertEqual(len(next_away_list), 1)
        self.assertEqual(next_away_list[0], self.next_away)
        
        # other_round_matches contains next_home, next_away, and other_round (all +-3 days)
        # total should be 3
        self.assertEqual(len(other_round_list), 3)
        self.assertIn(self.other_round, other_round_list)
        self.assertIn(self.next_home, other_round_list)
        self.assertIn(self.next_away, other_round_list)
        self.assertNotIn(self.base_match, other_round_list)
        
        # Check that translations/html sections are rendered
        html = response.content.decode('utf-8')
        self.assertIn('Next Matches', html)
        self.assertIn('Other Round Matches', html)
