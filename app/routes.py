from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from .db import get_db
from .ml_outlier import detectar_outliers

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    return redirect(url_for("main.listar_fornecedores"))


# ---------- Fornecedores (UC01) ----------
@bp.route("/fornecedores", methods=["GET", "POST"])
def listar_fornecedores():
    db = get_db()
    if request.method == "POST":
        nome = request.form["nome"].strip()
        if nome:
            db.execute("INSERT OR IGNORE INTO fornecedor (nome) VALUES (?)", (nome,))
            db.commit()
        db.close()
        return redirect(url_for("main.listar_fornecedores"))

    fornecedores = db.execute("SELECT * FROM fornecedor ORDER BY nome").fetchall()
    db.close()
    return render_template("fornecedores.html", fornecedores=fornecedores)


# ---------- Produtos (UC02) ----------
@bp.route("/produtos", methods=["GET", "POST"])
def listar_produtos():
    db = get_db()
    if request.method == "POST":
        nome = request.form["nome"].strip()
        unidade = request.form.get("unidade", "").strip()
        if nome:
            db.execute("INSERT INTO produto (nome, unidade) VALUES (?, ?)", (nome, unidade))
            db.commit()
        db.close()
        return redirect(url_for("main.listar_produtos"))

    produtos = db.execute("SELECT * FROM produto ORDER BY nome").fetchall()
    db.close()
    return render_template("produtos.html", produtos=produtos)


# ---------- Registrar Cotação (UC03) + módulo de outlier ----------
@bp.route("/cotacoes/nova", methods=["GET", "POST"])
def registrar_cotacao():
    db = get_db()

    if request.method == "POST":
        produto_id = request.form["produto_id"]
        fornecedor_id = request.form["fornecedor_id"]
        preco = float(request.form["preco"])
        data_cotacao = request.form["data_cotacao"]  # vem do calendário HTML, formato YYYY-MM-DD sempre
        mes_referencia = data_cotacao[:7]  # deriva o mês direto da data — nunca digitado à mão, nunca diverge

        # checa outlier contra as outras cotações já registradas do mesmo produto/mês
        outras = db.execute(
            "SELECT preco FROM cotacao WHERE produto_id = ? AND mes_referencia = ?",
            (produto_id, mes_referencia),
        ).fetchall()
        precos = [row["preco"] for row in outras] + [preco]
        resultado = detectar_outliers(precos)
        suspeito = resultado[-1][1]  # o preço que acabou de entrar é o último da lista

        db.execute(
            """INSERT OR REPLACE INTO cotacao (produto_id, fornecedor_id, preco, mes_referencia)
               VALUES (?, ?, ?, ?)""",
            (produto_id, fornecedor_id, preco, mes_referencia),
        )
        db.commit()
        db.close()

        if suspeito:
            flash(f"⚠️ Preço R$ {preco:.2f} parece fora do padrão pra esse produto — confere antes de fechar o pedido.", "warning")
        else:
            flash("Cotação registrada.", "success")

        return redirect(url_for("main.registrar_cotacao"))

    produtos = db.execute("SELECT * FROM produto ORDER BY nome").fetchall()
    fornecedores = db.execute("SELECT * FROM fornecedor ORDER BY nome").fetchall()
    db.close()
    data_hoje = date.today().isoformat()
    return render_template("registrar_cotacao.html", produtos=produtos, fornecedores=fornecedores, data_hoje=data_hoje)


# ---------- Consolidado Mensal — aplica RN01 ----------
@bp.route("/consolidado/<mes>")
def consolidado(mes):
    db = get_db()
    vencedoras = db.execute(
        """
        SELECT p.nome AS produto, f.nome AS fornecedor_vencedor, c.preco
        FROM cotacao c
        JOIN produto p ON p.id = c.produto_id
        JOIN fornecedor f ON f.id = c.fornecedor_id
        WHERE c.mes_referencia = ?
        AND c.preco = (
            SELECT MIN(c2.preco) FROM cotacao c2
            WHERE c2.produto_id = c.produto_id AND c2.mes_referencia = c.mes_referencia
        )
        ORDER BY p.nome
        """,
        (mes,),
    ).fetchall()
    db.close()
    return render_template("consolidado.html", vencedoras=vencedoras, mes=mes)


# ---------- Todas as Cotações do mês, lado a lado (igual a planilha antiga) ----------
@bp.route("/cotacoes/todas/<mes>")
def todas_cotacoes(mes):
    db = get_db()

    meses_disponiveis = [
        r["mes_referencia"]
        for r in db.execute(
            "SELECT DISTINCT mes_referencia FROM cotacao ORDER BY mes_referencia DESC"
        ).fetchall()
    ]

    rows = db.execute(
        """
        SELECT c.id AS cotacao_id, p.nome AS produto, f.nome AS fornecedor, c.preco
        FROM cotacao c
        JOIN produto p ON p.id = c.produto_id
        JOIN fornecedor f ON f.id = c.fornecedor_id
        WHERE c.mes_referencia = ?
        ORDER BY p.nome, f.nome
        """,
        (mes,),
    ).fetchall()
    db.close()

    fornecedores = sorted({r["fornecedor"] for r in rows})

    produtos = {}
    for r in rows:
        produtos.setdefault(r["produto"], {})[r["fornecedor"]] = {"preco": r["preco"], "id": r["cotacao_id"]}

    tabela = []
    for produto, precos in produtos.items():
        menor = min(v["preco"] for v in precos.values()) if precos else None
        tabela.append({"produto": produto, "precos": precos, "menor": menor})

    return render_template(
        "todas_cotacoes.html",
        fornecedores=fornecedores,
        tabela=tabela,
        mes=mes,
        meses_disponiveis=meses_disponiveis,
    )


# ---------- Excluir uma cotação registrada errada ----------
@bp.route("/cotacoes/excluir", methods=["POST"])
def excluir_cotacao():
    cotacao_id = request.form["cotacao_id"]
    mes = request.form.get("mes")

    db = get_db()
    db.execute("DELETE FROM cotacao WHERE id = ?", (cotacao_id,))
    db.commit()
    db.close()

    flash("Cotação excluída.", "success")
    if mes:
        return redirect(url_for("main.todas_cotacoes", mes=mes))
    return redirect(url_for("main.registrar_cotacao"))


# ---------- Pedido de Compra agrupado por fornecedor (aplica RN01) ----------
@bp.route("/pedido/<mes>")
def pedido_por_fornecedor(mes):
    db = get_db()
    vencedoras = db.execute(
        """
        SELECT p.nome AS produto, f.nome AS fornecedor, c.preco
        FROM cotacao c
        JOIN produto p ON p.id = c.produto_id
        JOIN fornecedor f ON f.id = c.fornecedor_id
        WHERE c.mes_referencia = ?
        AND c.preco = (
            SELECT MIN(c2.preco) FROM cotacao c2
            WHERE c2.produto_id = c.produto_id AND c2.mes_referencia = c.mes_referencia
        )
        ORDER BY f.nome, p.nome
        """,
        (mes,),
    ).fetchall()
    db.close()

    por_fornecedor = {}
    for r in vencedoras:
        por_fornecedor.setdefault(r["fornecedor"], []).append({"produto": r["produto"], "preco": r["preco"]})

    fornecedores = sorted(por_fornecedor.keys())
    return render_template("pedido.html", por_fornecedor=por_fornecedor, fornecedores=fornecedores, mes=mes)


# ---------- Lista de Produtos do Mês (base pra futura UC06 — pendências) ----------
def _mes_anterior(mes):
    ano, m = map(int, mes.split("-"))
    if m == 1:
        return f"{ano - 1}-12"
    return f"{ano}-{m - 1:02d}"


@bp.route("/lista-mes/<mes>", methods=["GET", "POST"])
def lista_mes(mes):
    db = get_db()

    if request.method == "POST":
        if request.form.get("acao") == "copiar_anterior":
            mes_ant = _mes_anterior(mes)
            db.execute(
                """INSERT OR IGNORE INTO lista_mes (produto_id, mes_referencia)
                   SELECT produto_id, ? FROM lista_mes WHERE mes_referencia = ?""",
                (mes, mes_ant),
            )
            db.commit()
            flash(f"Lista copiada de {mes_ant}.", "success")
        else:
            selecionados = request.form.getlist("produto_id")
            db.execute("DELETE FROM lista_mes WHERE mes_referencia = ?", (mes,))
            for pid in selecionados:
                db.execute(
                    "INSERT INTO lista_mes (produto_id, mes_referencia) VALUES (?, ?)",
                    (pid, mes),
                )
            db.commit()
            flash("Lista do mês salva.", "success")
        db.close()
        return redirect(url_for("main.lista_mes", mes=mes))

    produtos = db.execute("SELECT * FROM produto ORDER BY nome").fetchall()
    selecionados_ids = {
        r["produto_id"]
        for r in db.execute(
            "SELECT produto_id FROM lista_mes WHERE mes_referencia = ?", (mes,)
        ).fetchall()
    }

    mes_ant = _mes_anterior(mes)
    tem_lista_anterior = db.execute(
        "SELECT 1 FROM lista_mes WHERE mes_referencia = ? LIMIT 1", (mes_ant,)
    ).fetchone() is not None

    db.close()
    return render_template(
        "lista_mes.html",
        produtos=produtos,
        selecionados_ids=selecionados_ids,
        mes=mes,
        mes_anterior=mes_ant,
        tem_lista_anterior=tem_lista_anterior,
    )
