-- Dados FICTÍCIOS para desenvolvimento. Nunca coloque dados reais aqui.
-- Os produtos vêm do upload de dados_exemplo/produtos_exemplo.csv (como gerente).
INSERT INTO farmacias (id, nome)
VALUES ('11111111-1111-1111-1111-111111111111', 'Farmácia Exemplo (fictícia)')
ON CONFLICT DO NOTHING;