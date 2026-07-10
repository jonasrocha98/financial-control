"""Projeção das compras parceladas: quanto está comprometido e quando alivia.

Parcelas NÃO são somadas ao orçamento aqui — cada uma já existe como um
DailyExpense no mês em que cai. Este módulo só olha para o futuro.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from ..extensions import db
from ..models import Installment

MESES_PT = ["", "jan", "fev", "mar", "abr", "mai", "jun",
            "jul", "ago", "set", "out", "nov", "dez"]


def _q(v) -> Decimal:
    return Decimal(str(v or 0)).quantize(Decimal("0.01"))


def _soma(mes_base: tuple[int, int], n: int) -> tuple[int, int]:
    ano, mes = mes_base
    total = mes - 1 + n
    return ano + total // 12, total % 12 + 1


@dataclass
class Alivio:
    """Um momento futuro em que parcelas terminam e liberam dinheiro por mês."""
    meses_ate_la: int
    ano: int
    mes: int
    valor_liberado: Decimal
    acumulado: Decimal
    compras: list[str] = field(default_factory=list)

    @property
    def rotulo(self) -> str:
        return f"{MESES_PT[self.mes]}/{str(self.ano)[2:]}"


@dataclass
class ProjecaoParcelas:
    ativas: list[Installment]
    comprometido_mensal: Decimal   # quanto sai por mês hoje
    divida_restante: Decimal       # soma de tudo que ainda será pago
    alivios: list[Alivio]

    @property
    def tem_parcelas(self) -> bool:
        return bool(self.ativas)


def projetar(household_id: int) -> ProjecaoParcelas:
    todas = db.session.scalars(
        db.select(Installment).where(Installment.household_id == household_id)
    ).all()
    ativas = [p for p in todas if p.remaining > 0]
    ativas.sort(key=lambda p: (p.remaining, -float(p.amount)))

    comprometido = _q(sum((p.amount for p in ativas), start=Decimal(0)))
    divida = _q(sum((p.total_remaining for p in ativas), start=Decimal(0)))

    # Agrupa as compras que terminam no mesmo mês
    por_prazo: dict[int, list[Installment]] = {}
    for p in ativas:
        por_prazo.setdefault(p.remaining, []).append(p)

    alivios, acumulado = [], Decimal(0)
    for prazo in sorted(por_prazo):
        grupo = por_prazo[prazo]
        valor = _q(sum((p.amount for p in grupo), start=Decimal(0)))
        acumulado = _q(acumulado + valor)
        base = grupo[0].reference_month
        ano, mes = _soma((base.year, base.month), prazo)
        alivios.append(Alivio(
            meses_ate_la=prazo, ano=ano, mes=mes,
            valor_liberado=valor, acumulado=acumulado,
            compras=[p.name for p in grupo],
        ))

    return ProjecaoParcelas(ativas=ativas, comprometido_mensal=comprometido,
                            divida_restante=divida, alivios=alivios)
