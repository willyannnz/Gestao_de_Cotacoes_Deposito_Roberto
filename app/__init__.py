from datetime import date
from flask import Flask
from .db import init_db


def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.secret_key = "dev-chave-temporaria-trocar-depois"  # troca isso quando for pra produção

    init_db()

    from .routes import bp
    app.register_blueprint(bp)

    @app.context_processor
    def inject_mes_atual():
        return {"mes_atual_nav": date.today().strftime("%Y-%m")}

    return app
