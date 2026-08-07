-- Inserção de Ligas e Países (Baseado em matches/utils.py)
-- Execute este script no seu MySQL Workbench no banco de dados de produção.

INSERT INTO matches_league (name, country) VALUES
('Premier League', 'Inglaterra'),
('La Liga', 'Espanha'),
('Brasileirão', 'Brasil'),
('Serie A', 'Italia'),
('Bundesliga', 'Alemanha'),
('Ligue 1', 'Franca'),
('Eredivisie', 'Holanda'),
('Pro League', 'Belgica'),
('Premier League', 'Russia'),
('Premier League', 'Ucrania'),
('Allsvenskan', 'Suecia'),
('Eliteserien', 'Noruega'),
('Superliga', 'Dinamarca'),
('Veikkausliiga', 'Finlandia'),
('Super League', 'Grecia'),
('J1 League', 'Japao'),
('K League 1', 'Coreia do Sul'),
('Super League', 'China'),
('A League', 'Australia'),
('Liga Profesional', 'Argentina'),
('Bundesliga', 'Austria'),
('Super League', 'Suica'),
('First League', 'Republica Tcheca'),
('Ekstraklasa', 'Polonia'),
('Premiership', 'Escocia'),
('Cymru Premier', 'Gales'),
('Premier Division', 'Irlanda'),
('Primera A', 'Colombia'),
('Primera Division', 'Chile'),
('Liga MX', 'Mexico'),
('Primera Division', 'Uruguai'),
('Primeira Liga', 'Portugal'),
('MLS', 'Estados Unidos'),
('Super Lig', 'Turquia');

-- Nota: O comando acima irá falhar se já existirem ligas duplicadas (não há constraint unique por padrão no Django, mas é bom evitar).
-- Se quiser garantir que não duplique, use INSERT IGNORE ou verifique antes.
-- Como o banco está "vazio" para esses países, o INSERT simples deve funcionar.
