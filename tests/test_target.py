"""Meta de renda: gross-up do investimento e projeção das parcelas."""
from datetime import date
from decimal import Decimal

import pytest

from app.extensions import db
from app.models import DailyExpense, FixedExpense, Income, Installment
from app.services.installments import projetar
from app.services.target import Meta, calcular_meta


# --------------------------------------------------------------- gross-up
class _MetaFake:
    """com_investimento() só depende de custo_vida — testamos isolado."""
    custo_vida = Decimal("3600.00")
    com_investimento = Meta.com_investimento


def test_gross_up_nao_e_simples_percentual():
    m = _MetaFake()
    # 10% de 3600 = 360. Somar daria 3960. Mas o certo é 3600/0.9 = 4000.
    assert m.com_investimento(Decimal(10)) == Decimal("4000.00")
    assert m.com_investimento(Decimal(10)) != Decimal("3960.00")


def test_gross_up_zero_por_cento_e_o_proprio_custo():
    assert _MetaFake().com_investimento(Decimal(0)) == Decimal("3600.00")


def test_gross_up_investe_exatamente_o_percentual():
    m = _MetaFake()
    alvo = m.com_investimento(Decimal(20))
    assert alvo == Decimal("4500.00")
    # investindo 20% de 4500 = 900, sobram 3600 = custo de vida. Fecha.
    assert alvo - alvo * Decimal("0.20") == m.custo_vida


def test_gross_up_cem_por_cento_nao_explode():
    assert _MetaFake().com_investimento(Decimal(100)) == Decimal("0.00")


# ------------------------------------------------------------- projeção
def _parcela(household, nome, valor, atual, total, ref=date(2026, 7, 1)):
    p = Installment(household_id=household.id, name=nome, amount=Decimal(valor),
                    total_installments=total, current_installment=atual, reference_month=ref)
    db.session.add(p)
    db.session.commit()
    return p


def test_projecao_sem_parcelas(app, household):
    p = projetar(household.id)
    assert not p.tem_parcelas
    assert p.comprometido_mensal == Decimal("0.00")
    assert p.alivios == []


def test_quitada_nao_compromete_nada(app, household):
    _parcela(household, "Fim", "50", atual=6, total=6)
    p = projetar(household.id)
    assert p.ativas == []
    assert p.comprometido_mensal == Decimal("0.00")


def test_comprometido_e_divida(app, household):
    _parcela(household, "A", "100", atual=8, total=12)   # faltam 4
    _parcela(household, "B", "50", atual=5, total=6)     # falta 1
    p = projetar(household.id)
    assert p.comprometido_mensal == Decimal("150.00")
    assert p.divida_restante == Decimal("450.00")        # 100*4 + 50*1


def test_alivio_acumula_na_ordem_de_termino(app, household):
    _parcela(household, "Curta", "50", atual=5, total=6)    # falta 1 -> ago/26
    _parcela(household, "Longa", "100", atual=8, total=12)  # faltam 4 -> nov/26
    p = projetar(household.id)
    assert [a.meses_ate_la for a in p.alivios] == [1, 4]
    assert p.alivios[0].valor_liberado == Decimal("50.00")
    assert p.alivios[0].acumulado == Decimal("50.00")
    assert p.alivios[1].acumulado == Decimal("150.00")
    assert p.alivios[0].rotulo == "ago/26"
    assert p.alivios[1].rotulo == "nov/26"


def test_parcelas_que_terminam_juntas_sao_agrupadas(app, household):
    _parcela(household, "X", "30", atual=5, total=6)
    _parcela(household, "Y", "20", atual=5, total=6)
    p = projetar(household.id)
    assert len(p.alivios) == 1
    assert p.alivios[0].valor_liberado == Decimal("50.00")
    assert sorted(p.alivios[0].compras) == ["X", "Y"]


def test_alivio_vira_o_ano(app, household):
    _parcela(household, "Longa", "10", atual=1, total=7, ref=date(2026, 11, 1))
    p = projetar(household.id)
    assert (p.alivios[0].ano, p.alivios[0].mes) == (2027, 5)


# ----------------------------------------------------------------- meta
def test_meta_ignora_o_mes_corrente_e_as_parcelas_no_recorrente(app, household):
    uid = household.users[0].id
    db.session.add_all([
        FixedExpense(household_id=household.id, name="Aluguel", amount=Decimal("1000")),
        # mês fechado (2020, bem no passado)
        Income(household_id=household.id, user_id=uid, description="Salário",
               amount=Decimal("3000"), date=date(2020, 1, 15), recurring=True),
        Income(household_id=household.id, user_id=uid, description="Venda",
               amount=Decimal("200"), date=date(2020, 1, 20), recurring=False),
        DailyExpense(household_id=household.id, user_id=uid, description="Mercado",
                     amount=Decimal("800"), date=date(2020, 1, 10)),
        DailyExpense(household_id=household.id, user_id=uid, description="Parcela TV",
                     amount=Decimal("100"), date=date(2020, 1, 12), installment_info="3/6"),
        Income(household_id=household.id, user_id=uid, description="Salário",
               amount=Decimal("3000"), date=date(2020, 2, 15), recurring=True),
        DailyExpense(household_id=household.id, user_id=uid, description="Mercado",
                     amount=Decimal("800"), date=date(2020, 2, 10)),
    ])
    db.session.commit()

    m = calcular_meta(household.id)
    assert m.dados_suficientes
    assert m.meses_usados == ["01/2020", "02/2020"]
    # a parcela de 100 NÃO entra no gasto recorrente
    assert m.recorrente_mediano == Decimal("800.00")
    assert m.custo_vida == Decimal("1800.00")   # 1000 fixo + 800 recorrente
    assert m.renda_paralela_pico == Decimal("200.00")


def test_meta_sem_historico_avisa(app, household):
    m = calcular_meta(household.id)
    assert not m.dados_suficientes
