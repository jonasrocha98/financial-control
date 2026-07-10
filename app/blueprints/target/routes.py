from decimal import Decimal

from flask import render_template
from flask_login import current_user, login_required

from ...services.target import calcular_meta
from . import bp

PERCENTUAIS = [Decimal(5), Decimal(10), Decimal(15), Decimal(20)]


@bp.route("/")
@login_required
def index():
    meta = calcular_meta(current_user.household_id)

    cenarios = [
        {
            "pct": p,
            "renda_alvo": meta.com_investimento(p),
            "falta": meta.com_investimento(p) - meta.renda_mediana,
        }
        for p in PERCENTUAIS
    ]

    # Quanto a renda paralela precisaria crescer para fechar o buraco estrutural
    fator = None
    if meta.renda_paralela > 0 and meta.gap_sem_parcelas > 0:
        alvo = meta.renda_paralela + meta.gap_sem_parcelas
        bruto = (alvo / meta.renda_paralela).quantize(Decimal("0.1"))
        fator = str(bruto).replace(".", ",")  # pt-BR usa vírgula decimal

    return render_template(
        "target/index.html",
        meta=meta,
        cenarios=cenarios,
        fator_paralela=fator,
    )
