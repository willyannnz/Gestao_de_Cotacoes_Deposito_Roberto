from datetime import date
from flask import Flask
from .db import init_db

MESES_PT = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
            "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]


def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.secret_key = "dev-chave-temporaria-trocar-depois"  # troca isso quando for pra produção

    init_db()

    from .routes import bp
    app.register_blueprint(bp)

    @app.context_processor
    def inject_mes_atual():
        return {"mes_atual_nav": date.today().strftime("%Y-%m")}

    @app.template_filter("mes_extenso")
    def mes_extenso(valor):
        # "2026-10" -> "Outubro de 2026"; se o valor não for um mês válido, devolve como veio
        try:
            ano, mes = str(valor).split("-")
            return f"{MESES_PT[int(mes) - 1].capitalize()} de {ano}"
        except (ValueError, IndexError):
            return valor

    return app
