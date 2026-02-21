
from django.core.management.base import BaseCommand
from django.db import connection, DatabaseError
from django.db.models import Q
from matches.models import League, Team, Match

class Command(BaseCommand):
    help = 'Cleans up duplicate/bad teams for Brazil'

    def handle(self, *args, **kwargs):
        country = "Brasil"
        leagues = League.objects.filter(name__icontains="Brasileir", country=country)
        if not leagues.exists():
            self.stdout.write(self.style.ERROR("No Brazil leagues found"))
            return

        # Map Bad Name -> Canonical Name
        merges = {
            "Mirassol FC": "Mirassol",
            "Chapecoense AF": "Chapecoense",
            "CA Mineiro": "Atletico-MG",
            "CA Paranaense": "Athletico-PR",
            "Coritiba FBC": "Coritiba",
            "Clube do Remo": "Remo",
            "RB Bragantino": "Bragantino",
            "Red Bull Bragantino": "Bragantino",
            "Sport Club do Recife": "Sport Recife",
            "CR Vasco da Gama": "Vasco",
            "Botafogo FR": "Botafogo",
            "Grêmio FBPA": "Gremio",
            "EC Bahia": "Bahia",
            "EC Vitória": "Vitoria",
            "Cuiabá EC": "Cuiaba",
            "Fortaleza EC": "Fortaleza",
            "Criciúma EC": "Criciuma",
            "AC Goianiense": "Atletico-GO",
            "Goiás EC": "Goias",
            "América FC": "America-MG",
            "Avaí FC": "Avai",
            "Guarani FC": "Guarani",
            "Ponte Preta": "Ponte Preta",
            "Vila Nova FC": "Vila Nova",
            "Novorizontino": "Novorizontino",
            "CRB": "CRB",
            "Ituano FC": "Ituano",
            "Botafogo FC SP": "Botafogo-SP",
            "Operário Ferroviário": "Operario",
            "Amazonas FC": "Amazonas",
            "Paysandu SC": "Paysandu",
            "Brusque FC": "Brusque",
            "São Bernardo FC": "Sao Bernardo",
            "Volta Redonda FC": "Volta Redonda",
            "Athletic Club": "Athletic Club",
            "Ferroviária": "Ferroviaria",
            "Ypiranga FC": "Ypiranga",
            "Londrina EC": "Londrina",
        }

        for league in leagues:
            self.stdout.write(self.style.SUCCESS(f"Processing league: {league.name} ({league.id})"))
            for bad_name, good_name in merges.items():
                self.merge_teams(league, bad_name, good_name)

            # Remover times lixo como "MATCHES"
            garbage_names = ["MATCHES", "Matches", "Match"]
            for gname in garbage_names:
                bad_team = Team.objects.filter(name__iexact=gname, league=league).first()
                if not bad_team:
                    continue
                self.stdout.write(self.style.WARNING(f"Deleting garbage team {bad_team.name} ({bad_team.id}) and its matches"))
                Match.objects.filter(Q(home_team=bad_team) | Q(away_team=bad_team)).delete()
                bad_team.delete()

    def merge_teams(self, league, bad_name, good_name):
        # Find Canonical Team
        good_team = Team.objects.filter(name__iexact=good_name, league=league).first()
        if not good_team:
            self.stdout.write(f"Canonical team not found: {good_name}. Skipping {bad_name}.")
            return

        # Find Bad Team
        # We search exactly for the bad name
        bad_team = Team.objects.filter(name__iexact=bad_name, league=league).first()
        if not bad_team:
            # self.stdout.write(f"Bad team not found: {bad_name}. Good.")
            return

        if bad_team.id == good_team.id:
            return

        self.stdout.write(f"Merging {bad_team.name} ({bad_team.id}) -> {good_team.name} ({good_team.id})")

        # Move Home Matches
        home_matches = Match.objects.filter(home_team=bad_team)
        for m in home_matches:
            # Check if match already exists for good_team (avoid duplicates)
            exists = Match.objects.filter(
                league=league,
                season=m.season,
                home_team=good_team,
                away_team=m.away_team, # Note: away_team might also be bad, but we handle one side at a time
                date=m.date
            ).exists()
            
            if exists:
                self.stdout.write(f"  Deleting duplicate match {m}")
                m.delete()
            else:
                self.stdout.write(f"  Moving match {m} to {good_team.name}")
                m.home_team = good_team
                m.save()

        # Move Away Matches
        away_matches = Match.objects.filter(away_team=bad_team)
        for m in away_matches:
            exists = Match.objects.filter(
                league=league,
                season=m.season,
                home_team=m.home_team,
                away_team=good_team,
                date=m.date
            ).exists()
            
            if exists:
                self.stdout.write(f"  Deleting duplicate match {m}")
                m.delete()
            else:
                self.stdout.write(f"  Moving match {m} to {good_team.name}")
                m.away_team = good_team
                m.save()

        # Delete Bad Team
        self.stdout.write(f"Deleting team {bad_team.name}")
        try:
            bad_team.delete()
        except DatabaseError as e:
            msg = str(e)
            if "matches_teamgoaltiming" in msg or "doesn't exist" in msg or "does not exist" in msg:
                self.stdout.write(self.style.WARNING(f"Direct delete failed due to missing table. Forcing raw delete of team {bad_team.id}."))
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM matches_team WHERE id = %s", [bad_team.id])
            else:
                raise
