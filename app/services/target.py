"""Quanto preciso faturar: ponto de equilíbrio e o gap até ele.

O investimento sai POR CIMA da renda, não do que sobra. Por isso a renda
necessária não é `custo + %`, e sim `custo / (1 - %)` — o gross-up.

Nada aqui usa IA: é mediana, soma e uma divisão.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import extract, func

from ..extensions import db
from ..models import DailyExpense, Income, InvestmentConfig
from .budget import _q, current_year_month, month_bounds
from .installments import ProjecaoParcelas, projetar

MIN_MESES = 2  # abaixo disso, mediana não significa nada


def _mediana(vals: list[Decimal]) -> Decimal:
    if not vals:
        return Decimal("0.00")
    return _q(statistics.median([float(v) for v in vals]))


@dataclass
class Meta:
    meses_usados: list[str]
    dados_suficientes: bool

    renda_mediana: Decimal
    renda_salario: Decimal      # entradas recorrentes
    renda_paralela: Decimal     # vendas, serviços, bicos
    renda_paralela_pico: Decimal

    fixo_mensal: Decimal
    recorrente_mediano: Decimal
    custo_vida: Decimal         # fixo + recorrente: o que NÃO acaba

    parcelas: ProjecaoParcelas
    investimento_pct: Decimal

    @property
    def ponto_equilibrio(self) -> Decimal:
        """Quanto faturar para cobrir tudo que você paga hoje."""
        return _q(self.custo_vida + self.parcelas.comprometido_mensal)

    @property
    def gap(self) -> Decimal:
        """Quanto falta por mês. Positivo = falta."""
        return _q(self.ponto_equilibrio - self.renda_mediana)

    @property
    def gap_sem_parcelas(self) -> Decimal:
        """O buraco estrutural, depois que as parcelas quitarem."""
        return _q(self.custo_vida - self.renda_mediana)

    @property
    def no_azul(self) -> bool:
        return self.gap <= 0

    def com_investimento(self, pct: Decimal) -> Decimal:
        """Renda necessária para cobrir o custo de vida E investir pct% dela."""
        pct = Decimal(str(pct))
        if pct >= 100:
            return Decimal("0.00")
        return _q(self.custo_vida / (Decimal(1) - pct / 100))

    @property
    def gap_semanal(self) -> Decimal:
        return _q(self.gap / Decimal("4.33")) if self.gap > 0 else Decimal("0.00")


def _meses_fechados(household_id: int) -> list[tuple[int, int]]:
    """Meses com lançamentos, exceto o corrente (que ainda está em curso)."""
    ano_atual, mes_atual = current_year_month()
    rows = db.session.execute(
        db.select(extract("year", DailyExpense.date), extract("month", DailyExpense.date))
        .where(DailyExpense.household_id == household_id)
        .group_by(extract("year", DailyExpense.date), extract("month", DailyExpense.date))
    ).all()
    meses = sorted((int(a), int(m)) for a, m in rows)
    return [(a, m) for a, m in meses if (a, m) < (ano_atual, mes_atual)]


def _soma_mes(model, household_id, ano, mes, *filtros) -> Decimal:
    q = db.select(func.coalesce(func.sum(model.amount), 0)).where(
        model.household_id == household_id,
        extract("year", model.date) == ano,
        extract("month", model.date) == mes,
        *filtros,
    )
    return _q(db.session.scalar(q))


def calcular_meta(household_id: int) -> Meta:
    from ..models import FixedExpense

    meses = _meses_fechados(household_id)
    rendas, salarios, paralelas, recorrentes = [], [], [], []

    for ano, mes in meses:
        rendas.append(_soma_mes(Income, household_id, ano, mes))
        salarios.append(_soma_mes(Income, household_id, ano, mes, Income.recurring.is_(True)))
        paralelas.append(_soma_mes(Income, household_id, ano, mes, Income.recurring.is_(False)))
        # gasto recorrente = dia a dia SEM as parcelas (parcelas terminam)
        recorrentes.append(_soma_mes(DailyExpense, household_id, ano, mes,
                                     DailyExpense.installment_info.is_(None)))

    # Fixos vigentes no mês corrente
    ano_atual, mes_atual = current_year_month()
    primeiro, ultimo = month_bounds(ano_atual, mes_atual)
    fixo = _q(db.session.scalar(
        db.select(func.coalesce(func.sum(FixedExpense.amount), 0)).where(
            FixedExpense.household_id == household_id,
            FixedExpense.active.is_(True),
            db.or_(FixedExpense.start_date.is_(None), FixedExpense.start_date <= ultimo),
            db.or_(FixedExpense.end_date.is_(None), FixedExpense.end_date >= primeiro),
        )))

    config = db.session.scalar(
        db.select(InvestmentConfig).where(InvestmentConfig.household_id == household_id))

    recorrente = _mediana(recorrentes)
    return Meta(
        meses_usados=[f"{m:02d}/{a}" for a, m in meses],
        dados_suficientes=len(meses) >= MIN_MESES,
        renda_mediana=_mediana(rendas),
        renda_salario=_mediana(salarios),
        renda_paralela=_mediana(paralelas),
        renda_paralela_pico=_q(max(paralelas)) if paralelas else Decimal("0.00"),
        fixo_mensal=fixo,
        recorrente_mediano=recorrente,
        custo_vida=_q(fixo + recorrente),
        parcelas=projetar(household_id),
        investimento_pct=_q(config.percentage if config else 0),
    )
