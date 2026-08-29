#!/usr/bin/env python
"""
MESCLAGEM DE TIMES DUPLICADOS (11/08/2026)
Move jogos/standings da duplicata para o time canônico e exclui a duplicata.
Detectado: 5 casos (4 por slug igual + Helsingborgs IF/Helsingborg).
Seguro: 0 conflitos de data em todos os casos (validado antes).
"""
import os, sys, django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from matches.models import Team, Match, LeagueStanding

# (id_canônico, id_duplicata, observação)
CASOS = [
    (3826, 14422, "St. Mirren / ST Mirren (Escócia)"),
    (4549, 14460, "Botafogo-PB / Botafogo PB (Série C)"),
    (14081, 14459, "Botafogo-SP / Botafogo SP (Série B)"),
    (14143, 14419, "Newell's Old Boys / Newells Old Boys (Argentina)"),
    (4687, 5185, "Helsingborgs IF / Helsingborg (Suécia Superettan)"),
]

def plural(n, s="jogo"):
    return f"{n} {s}{'s' if n != 1 else ''}"

def _exists_no_canon(dup_m, canon):
    """Retorna True se o jogo (dup_m) já existe no canônico (mesmo home+away+data exata)."""
    if not dup_m.date:
        return False
    return (
        Match.objects.filter(home_team=canon, away_team=dup_m.away_team, date=dup_m.date).exists()
        or Match.objects.filter(home_team=dup_m.away_team, away_team=canon, date=dup_m.date).exists()
    )

total = 0
for canon_id, dup_id, obs in CASOS:
    canon = Team.objects.filter(id=canon_id).first()
    dup = Team.objects.filter(id=dup_id).first()
    if not canon or not dup:
        print(f"⚠️  {obs}: canon={canon_id} ({canon}) dup={dup_id} ({dup}) — pulando (id não encontrado)")
        continue
    moved = 0
    deleted_dup = 0
    # 1º: identifica TODOS os jogos da duplicata que já existem no canônico (mesmo
    #    adversário + data exata, em qualquer orientação) e exclui ANTES de mover,
    #    para evitar colisão de unique_constraint durante a movimentação.
    for m in list(Match.objects.filter(home_team=dup)) + list(Match.objects.filter(away_team=dup)):
        if not m.date:
            continue
        # adversário = o time que NÃO é a duplicata
        oponente = m.away_team if m.home_team_id == dup.id else m.home_team
        ja_existe = (
            Match.objects.filter(home_team=canon, away_team=oponente, date=m.date).exclude(pk=m.pk).exists()
            or Match.objects.filter(home_team=oponente, away_team=canon, date=m.date).exclude(pk=m.pk).exists()
        )
        if ja_existe:
            m.delete()
            deleted_dup += 1
    # 2º: agora move os jogos restantes (sem conflito)
    for m in list(Match.objects.filter(home_team=dup)):
        m.home_team = canon
        m.save(update_fields=['home_team'])
        moved += 1
    for m in list(Match.objects.filter(away_team=dup)):
        m.away_team = canon
        m.save(update_fields=['away_team'])
        moved += 1
    # Move standings
    moved_stand = 0
    for s in LeagueStanding.objects.filter(team=dup):
        # evita duplicar standing com mesmo season no canon
        if LeagueStanding.objects.filter(team=canon, league=s.league, season=s.season).exists():
            s.delete()
        else:
            s.team = canon
            s.save(update_fields=['team'])
        moved_stand += 1
    # Exclui a duplicata
    n_matches = Match.objects.filter(home_team=dup).count() + Match.objects.filter(away_team=dup).count()
    if n_matches == 0:
        dup.delete()
        status = f"✅ {obs}: movidos {plural(moved)} + {deleted_dup} duplicadas excluídas; duplicata {dup.id} excluída"
    else:
        status = f"⚠️  {obs}: movidos {plural(moved)} ({deleted_dup} excluídas) mas {n_matches} jogos ainda referenciam o time — NÃO excluída"
    total += moved
    print(status)
    if '⚠️' in status:
        sys.exit(1)

print(f"\nTotal de jogos movidos: {total}")
print("Concluído.")
