"""Application factory."""
from flask import Flask

from config import Config, describe_db_target
from .extensions import csrf, db, login_manager, migrate


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Diagnóstico: um hostname errado na DATABASE_URL falha 100 linhas depois,
    # dentro do driver. Dizer para onde estamos conectando encurta a caçada.
    if not app.config.get("TESTING"):
        alvo = describe_db_target(app.config["SQLALCHEMY_DATABASE_URI"])
        print(f"[controle-financeiro] banco: {alvo}", flush=True)

    # Extensões
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Models (importados para o Alembic enxergar) + user_loader
    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Blueprints
    from .blueprints.auth import bp as auth_bp
    from .blueprints.dashboard import bp as dashboard_bp
    from .blueprints.expenses import bp as expenses_bp
    from .blueprints.income import bp as income_bp
    from .blueprints.purchases import bp as purchases_bp
    from .blueprints.settings import bp as settings_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(income_bp)
    app.register_blueprint(purchases_bp)
    app.register_blueprint(settings_bp)

    # Filtros de template
    from .utils import format_currency

    app.jinja_env.filters["money"] = format_currency

    return app
