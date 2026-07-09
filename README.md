# 💸 Controle Financeiro da Casa

Aplicativo web simples para organizar as finanças da casa de forma compartilhada.
Você e sua esposa lançam os gastos cada um do seu celular, alimentando o **mesmo
orçamento**, e o app calcula automaticamente quanto sobra e o que dá para comprar.

Tema **dark**, minimalista, responsivo e instalável como app no celular (PWA).

## ✨ Funcionalidades

- **Dashboard** — resumo do mês: entradas, reserva de investimento, gastos e a **sobra**, com gráficos.
- **Gastos fixos** — aluguel, internet, assinaturas... o que se repete todo mês.
- **Gastos do dia a dia** — mercado, transporte, lazer; lançamento rápido pelo celular.
- **Entradas** — salário e outras receitas (base para o cálculo de investimento).
- **Compras futuras** — lista priorizada que **se auto-organiza conforme a sobra**: mostra o que
  dá para comprar este mês e quanto falta para o resto. *(Pura lógica, sem IA.)*
- **Investimento** — configure um **% das entradas** para separar todo mês automaticamente.
- **Multiusuário** — várias pessoas na mesma "casa" via código de convite.

## 🧮 Como a sobra e as compras são calculadas (sem IA)

```
sobra = entradas − (entradas × % investimento) − gastos fixos − gastos do dia a dia
```

As compras futuras são ordenadas por prioridade (e prazo) e a sobra é distribuída de cima
para baixo: o que cabe é marcado como "dá para comprar agora", o resto mostra quanto falta.
Toda a regra está em [`app/services/`](app/services) e é coberta por testes.

## 🛠️ Tecnologias

- **Backend:** Python + Flask (app factory + blueprints)
- **Banco:** SQLAlchemy + Flask-Migrate · SQLite no dev, **Postgres** em produção
- **Auth:** Flask-Login · senhas com hash · CSRF em todos os formulários (Flask-WTF)
- **Frontend:** Jinja2 + CSS próprio (tema dark) + Chart.js · PWA
- **Deploy:** gunicorn + Render · Postgres na Supabase

## 🚀 Rodando localmente

```bash
# 1. Clonar e entrar na pasta
git clone https://github.com/jonasrocha98/financial-control.git
cd financial-control

# 2. Criar o ambiente virtual e instalar dependências
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate
pip install -r requirements.txt

# 3. Configurar variáveis de ambiente
cp .env.example .env        # no Windows: copy .env.example .env
# edite o .env e defina um SECRET_KEY (deixe DATABASE_URL vazio para usar SQLite)

# 4. Criar o banco
flask --app wsgi.py db upgrade

# 5. Rodar
flask --app wsgi.py run
# abra http://127.0.0.1:5000
```

Na primeira tela, **crie sua conta** (isso cria a "casa"). Em **Configurações** há um
**código de convite** — compartilhe com a outra pessoa para ela entrar na mesma casa.

## 🧪 Testes

```bash
pytest
```

Os testes cobrem o cálculo da sobra ([`tests/test_budget.py`](tests/test_budget.py)) e a
alocação das compras por prioridade ([`tests/test_planner.py`](tests/test_planner.py)).

## ☁️ Deploy (Render + Supabase)

1. **Banco (Supabase):** crie um projeto em [supabase.com](https://supabase.com), vá em
   *Project Settings → Database → Connection string (URI)* e copie a string.
2. **App (Render):** crie um *Web Service* apontando para este repositório. O
   [`render.yaml`](render.yaml) já define build e start.
3. No painel do Render, configure as variáveis de ambiente:
   - `DATABASE_URL` → a connection string da Supabase
   - `SECRET_KEY` → gere uma (o `render.yaml` já pede para gerar)
   - `FLASK_ENV=production`
4. O deploy roda `flask db upgrade` automaticamente e sobe o gunicorn.

> A Supabase faz **backups automáticos** do Postgres — seus dados ficam guardados sem
> esforço extra.

## 📁 Estrutura

```
app/
  models/        # tabelas (Household, User, Income, FixedExpense, DailyExpense, ...)
  blueprints/    # rotas por área (auth, dashboard, expenses, income, purchases, settings)
  services/      # budget.py (sobra) e planner.py (compras) — núcleo testável
  templates/     # páginas Jinja2 (tema dark)
  static/        # css, ícones, manifest e service worker (PWA)
tests/           # testes do núcleo de cálculo
migrations/      # migrations do banco (Alembic)
```

## 🔮 Próximos passos (ideias)

- Categorização automática de gastos por texto (aí sim com IA).
- Relatórios por categoria e comparação mês a mês.
- Metas de poupança e acompanhamento de investimentos.
- Exportação/backup adicional para o Google Drive.

---

Projeto pessoal, feito para uso da família. Sinta-se à vontade para usar como referência.
