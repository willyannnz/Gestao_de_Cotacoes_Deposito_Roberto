from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from .db import get_db
from .ml_outlier import detectar_outliers

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    mes_atual = date.today().strftime("%Y-%m")
    db = get_db()
    resumo = db.execute(
        """SELECT COUNT(DISTINCT i.produto_id) AS produtos,
                  COUNT(DISTINCT c.id) AS cotacoes,
                  COUNT(DISTINCT c.fornecedor_id) AS fornecedores
           FROM cotacao_mensal_item i
           LEFT JOIN cotacao c ON c.produto_id = i.produto_id AND c.mes_referencia = i.mes_referencia
           WHERE i.mes_referencia = ?""", (mes_atual,)
    ).fetchone()
    meses = db.execute(
        """SELECT mes_referencia FROM cotacao_mensal
           ORDER BY mes_referencia DESC LIMIT 6"""
    ).fetchall()
    db.close()
    return render_template("inicio.html", mes_atual=mes_atual, resumo=resumo, meses=meses)


# ---------- Tabelas mensais de cotação ----------
@bp.route("/meses", methods=["GET", "POST"])
def lista_meses():
    db = get_db()
    if request.method == "POST":
        mes = request.form.get("mes", "").strip()
        try:
            datetime.strptime(mes, "%Y-%m")
        except ValueError:
            flash("Informe um mês válido.", "warning")
        else:
            db.execute("INSERT OR IGNORE INTO cotacao_mensal (mes_referencia) VALUES (?)", (mes,))
            db.commit()
            db.close()
            return redirect(url_for("main.editar_lista_mes", mes=mes))
        db.close()
        return redirect(url_for("main.lista_meses"))

    meses = db.execute(
        """SELECT m.mes_referencia, COUNT(DISTINCT i.produto_id) AS total_produtos,
                  COUNT(DISTINCT c.produto_id) AS produtos_com_cotacao
           FROM cotacao_mensal m
           LEFT JOIN cotacao_mensal_item i ON i.mes_referencia = m.mes_referencia
           LEFT JOIN cotacao c ON c.mes_referencia = i.mes_referencia AND c.produto_id = i.produto_id
           GROUP BY m.mes_referencia ORDER BY m.mes_referencia DESC"""
    ).fetchall()
    db.close()
    return render_template("meses.html", meses=meses, mes_atual=date.today().strftime("%Y-%m"))


@bp.route("/meses/<mes>", methods=["GET", "POST"])
def editar_lista_mes(mes):
    db = get_db()
    db.execute("INSERT OR IGNORE INTO cotacao_mensal (mes_referencia) VALUES (?)", (mes,))
    if request.method == "POST":
        acao = request.form.get("acao")
        if acao == "adicionar":
            nome = request.form.get("novo_produto_nome", "").strip()
            unidade = request.form.get("novo_produto_unidade", "").strip()
            produto_id = request.form.get("produto_id")
            if nome:
                cur = db.execute("INSERT INTO produto (nome, unidade) VALUES (?, ?)", (nome, unidade))
                produto_id = cur.lastrowid
            quantidade = request.form.get("quantidade", "1")
            try:
                quantidade = float(quantidade)
                if quantidade <= 0:
                    raise ValueError
            except ValueError:
                flash("A quantidade precisa ser maior que zero.", "warning")
            else:
                if produto_id:
                    db.execute(
                        "INSERT OR IGNORE INTO cotacao_mensal_item (mes_referencia, produto_id, quantidade) VALUES (?, ?, ?)",
                        (mes, produto_id, quantidade),
                    )
                    flash("Produto incluído na tabela do mês.", "success")
                else:
                    flash("Escolha um produto cadastrado ou informe um nome novo.", "warning")
        elif acao == "remover":
            item_id = request.form.get("item_id")
            item = db.execute("SELECT produto_id FROM cotacao_mensal_item WHERE id = ? AND mes_referencia = ?", (item_id, mes)).fetchone()
            if item:
                tem_cotacao = db.execute(
                    "SELECT 1 FROM cotacao WHERE mes_referencia = ? AND produto_id = ? LIMIT 1", (mes, item["produto_id"])
                ).fetchone()
                if tem_cotacao:
                    flash("Esse produto já tem cotações neste mês; mantenha-o na tabela para preservar o contexto.", "warning")
                else:
                    db.execute("DELETE FROM cotacao_mensal_item WHERE id = ?", (item_id,))
                    flash("Produto removido da tabela do mês.", "success")
        elif acao == "quantidade":
            item_id = request.form.get("item_id")
            try:
                quantidade = float(request.form.get("quantidade", ""))
                if quantidade <= 0:
                    raise ValueError
                db.execute(
                    "UPDATE cotacao_mensal_item SET quantidade = ? WHERE id = ? AND mes_referencia = ?",
                    (quantidade, item_id, mes),
                )
                flash("Quantidade atualizada.", "success")
            except ValueError:
                flash("A quantidade precisa ser maior que zero.", "warning")
        db.commit()
        db.close()
        return redirect(url_for("main.editar_lista_mes", mes=mes))

    produtos = db.execute("SELECT * FROM produto ORDER BY nome").fetchall()
    itens = db.execute(
        """SELECT i.id, i.quantidade, p.id AS produto_id, p.nome, p.unidade,
                  COUNT(c.id) AS total_cotacoes
           FROM cotacao_mensal_item i JOIN produto p ON p.id = i.produto_id
           LEFT JOIN cotacao c ON c.produto_id = i.produto_id AND c.mes_referencia = i.mes_referencia
           WHERE i.mes_referencia = ? GROUP BY i.id ORDER BY p.nome""", (mes,)
    ).fetchall()
    db.close()
    return render_template("mes_cotacao.html", mes=mes, produtos=produtos, itens=itens)


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


@bp.route("/produtos/<int:produto_id>/editar", methods=["POST"])
def editar_produto(produto_id):
    nome = request.form["nome"].strip()
    unidade = request.form.get("unidade", "").strip()
    db = get_db()
    if nome:
        db.execute("UPDATE produto SET nome = ?, unidade = ? WHERE id = ?", (nome, unidade, produto_id))
        db.commit()
        flash("Produto atualizado.", "success")
    else:
        flash("O nome não pode ficar vazio.", "warning")
    db.close()
    return redirect(url_for("main.listar_produtos"))


@bp.route("/produtos/<int:produto_id>/excluir", methods=["POST"])
def excluir_produto(produto_id):
    db = get_db()
    em_uso = db.execute(
        """SELECT 1 FROM cotacao WHERE produto_id = ?
           UNION SELECT 1 FROM cotacao_mensal_item WHERE produto_id = ? LIMIT 1""",
        (produto_id, produto_id),
    ).fetchone()
    if em_uso:
        flash("Esse produto já tem cotação registrada ou está em alguma tabela mensal — não dá pra excluir sem perder histórico. Edita o nome se for só correção.", "warning")
    else:
        db.execute("DELETE FROM produto WHERE id = ?", (produto_id,))
        db.commit()
        flash("Produto removido.", "success")
    db.close()
    return redirect(url_for("main.listar_produtos"))


# ---------- Registrar Cotação (UC03) + módulo de outlier ----------
@bp.route("/cotacoes/nova", methods=["GET", "POST"])
def registrar_cotacao():
    db = get_db()

    if request.method == "POST":
        produto_id = request.form.get("produto_id")
        fornecedor_id = request.form.get("fornecedor_id")
        novo_fornecedor_nome = request.form.get("novo_fornecedor_nome", "").strip()

        if not produto_id:
            flash("Escolha um produto da tabela mensal.", "warning")
            db.close()
            return redirect(url_for("main.registrar_cotacao", mes=request.form.get("mes_referencia", "")))

        if not fornecedor_id and not novo_fornecedor_nome:
            flash("Escolhe um fornecedor já cadastrado ou digita um novo.", "warning")
            db.close()
            return redirect(url_for("main.registrar_cotacao", mes=request.form.get("mes_referencia", "")))

        # cria fornecedor na hora, se for o caso
        if novo_fornecedor_nome:
            cur = db.execute(
                "INSERT OR IGNORE INTO fornecedor (nome) VALUES (?)", (novo_fornecedor_nome,)
            )
            row = db.execute(
                "SELECT id FROM fornecedor WHERE nome = ?", (novo_fornecedor_nome,)
            ).fetchone()
            fornecedor_id = row["id"]

        preco = float(request.form["preco"])
        mes_referencia = request.form.get("mes_referencia", "").strip()
        try:
            datetime.strptime(mes_referencia, "%Y-%m")
        except ValueError:
            flash("Mês de cotação inválido.", "warning")
            db.close()
            return redirect(url_for("main.lista_meses"))

        if not db.execute(
            "SELECT 1 FROM cotacao_mensal_item WHERE mes_referencia = ? AND produto_id = ?",
            (mes_referencia, produto_id),
        ).fetchone():
            flash("Inclua esse produto na tabela do mês antes de registrar a cotação.", "warning")
            db.close()
            return redirect(url_for("main.editar_lista_mes", mes=mes_referencia))

        # checa outlier contra as outras cotações já registradas do mesmo produto/mês
        outras = db.execute(
            "SELECT preco FROM cotacao WHERE produto_id = ? AND mes_referencia = ?",
            (produto_id, mes_referencia),
        ).fetchall()
        precos = [row["preco"] for row in outras] + [preco]
        resultado = detectar_outliers(precos)
        suspeito = resultado[-1][1]  # o preço que acabou de entrar é o último da lista

        db.execute(
            """INSERT INTO cotacao (produto_id, fornecedor_id, preco, mes_referencia)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(produto_id, fornecedor_id, mes_referencia)
               DO UPDATE SET preco = excluded.preco, data_registro = CURRENT_TIMESTAMP""",
            (produto_id, fornecedor_id, preco, mes_referencia),
        )
        db.commit()
        db.close()

        if suspeito:
            flash(f"⚠️ Preço R$ {preco:.2f} parece fora do padrão pra esse produto — confere antes de fechar o pedido.", "warning")
        else:
            flash("Cotação registrada.", "success")

        return redirect(url_for("main.registrar_cotacao", mes=mes_referencia))

    mes = request.args.get("mes", date.today().strftime("%Y-%m"))
    produtos = db.execute(
        "SELECT p.* FROM produto p JOIN cotacao_mensal_item i ON i.produto_id = p.id WHERE i.mes_referencia = ? ORDER BY p.nome",
        (mes,),
    ).fetchall()
    db.execute("INSERT OR IGNORE INTO cotacao_mensal (mes_referencia) VALUES (?)", (mes,))
    db.commit()
    fornecedores = db.execute("SELECT * FROM fornecedor ORDER BY nome").fetchall()
    db.close()
    return render_template("registrar_cotacao.html", produtos=produtos, fornecedores=fornecedores, mes=mes)


# ---------- Consolidado Mensal — aplica RN01 ----------
@bp.route("/consolidado/<mes>")
def consolidado(mes):
    db = get_db()
    vencedoras = db.execute(
        """
        SELECT p.nome AS produto, f.nome AS fornecedor_vencedor, c.preco, i.quantidade,
               c.preco * i.quantidade AS subtotal
        FROM cotacao c
        JOIN produto p ON p.id = c.produto_id
        JOIN fornecedor f ON f.id = c.fornecedor_id
        JOIN cotacao_mensal_item i ON i.produto_id = c.produto_id AND i.mes_referencia = c.mes_referencia
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
        SELECT p.id AS produto_id, p.nome AS produto, f.nome AS fornecedor,
               c.id AS cotacao_id, c.preco
        FROM cotacao_mensal_item i
        JOIN produto p ON p.id = i.produto_id
        LEFT JOIN cotacao c ON c.produto_id = i.produto_id AND c.mes_referencia = i.mes_referencia
        LEFT JOIN fornecedor f ON f.id = c.fornecedor_id
        WHERE i.mes_referencia = ?
        ORDER BY p.nome, f.nome
        """,
        (mes,),
    ).fetchall()
    db.close()

    fornecedores = sorted({r["fornecedor"] for r in rows if r["fornecedor"]})

    produtos = {}
    for r in rows:
        produtos.setdefault(r["produto"], {})
        if r["fornecedor"]:
            produtos[r["produto"]][r["fornecedor"]] = {"preco": r["preco"], "id": r["cotacao_id"]}

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
        SELECT p.nome AS produto, p.unidade AS unidade, f.nome AS fornecedor, c.preco, i.quantidade
        FROM cotacao c
        JOIN produto p ON p.id = c.produto_id
        JOIN fornecedor f ON f.id = c.fornecedor_id
        JOIN cotacao_mensal_item i ON i.produto_id = c.produto_id AND i.mes_referencia = c.mes_referencia
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
        por_fornecedor.setdefault(r["fornecedor"], []).append(
            {"produto": r["produto"], "unidade": r["unidade"], "preco": r["preco"], "quantidade": r["quantidade"]}
        )

    fornecedores = sorted(por_fornecedor.keys())
    return render_template("pedido.html", por_fornecedor=por_fornecedor, fornecedores=fornecedores, mes=mes)
