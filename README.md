# Sistema de Gestão de Cotações — Depósito do Roberto

Trabalho de Análise e Projeto de Sistemas (APS). Sistema pra decidir a compra mensal de bebidas comparando cotações de vários fornecedores, aplicando a RN01 (menor preço por item individual, nunca pelo pacote fechado do fornecedor).

## Stack
- Python 3 + Flask
- SQLite puro (sem ORM) — schema em `database/schema.sql`
- Bootstrap 5 + CSS próprio (`static/style.css`)
- Módulo de ML (Seção 8): detecção de preço suspeito (outlier, método IQR) usando a biblioteca padrão `statistics`

## Como rodar

```
python -m venv venv
venv\Scripts\activate      (Windows)
pip install -r requirements.txt
python app.py
```

Acessa em http://localhost:5000

## Estrutura
- `app/` — código Flask (rotas, conexão com banco, módulo de ML)
- `database/schema.sql` — schema do banco, traduzido do Diagrama de Classes UML
- `templates/` — páginas HTML (Bootstrap + estilo próprio)
- `static/style.css` — identidade visual do sistema
- `static/logo-deposito.png` — logo completa exibida na tela inicial

## Regras de negócio implementadas
- **RN01**: fechamento de compra pelo menor preço por item individual (query SQL com `MIN` + `JOIN`)
- **Detecção de outlier**: preço fora do padrão é sinalizado na hora do registro, comparando com as outras cotações do mesmo produto/mês (método IQR)
- **Tabela mensal variável**: cada mês mantém seus próprios produtos e quantidades; o consolidado calcula subtotais com base na quantidade do mês

## Fluxo mensal
1. Abra **Tabelas Mensais** e crie/abra o mês.
2. Inclua os produtos desejados e informe as quantidades daquele mês.
3. Registre os preços dos fornecedores apenas para os produtos da tabela.
4. Abra as listas por fornecedor e copie separadamente a lista de cada empresa para colar no WhatsApp.

As listas antigas de produtos e suas cotações são preservadas. Na primeira inicialização após a atualização, os produtos já cotados são incluídos automaticamente nas tabelas dos respectivos meses com quantidade inicial 1. O sistema prepara e copia separadamente a lista de cada fornecedor para a área de transferência; o envio é feito manualmente pelo WhatsApp.

## Origem do projeto
Baseado numa planilha real usada no depósito da família antes do sistema existir — a lógica de "menor preço" já era aplicada manualmente em Excel (`MIN` + `INDEX/MATCH`).
