"""Reconciliação: confere se a 'sobra' calculada bate com o dinheiro real.

Identidade que precisa fechar (jan..jun):
    entradas - despesas = Δsaldo_conta + Δcaixinha + Δdívida_cartão

Se não fechar, alguma classificação está errada ou existe dinheiro fora do Nubank.
"""
from __future__ import annotations

import io
import re
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ofx_to_planilha import EXTRATOS, PARCELA_RE, classificar, parse  # noqa: E402

JAN, JUN = "2026-01", "2026-06"


def brl(v) -> str:
    v = Decimal(str(v)).quantize(Decimal("0.01"))
    i, _, c = f"{v:,.2f}".partition(".")
    return f"{i.replace(',', '.')},{c}"


def main():
    trns = []
    for f in sorted(EXTRATOS.glob("*.ofx")):
        trns.extend(parse(f))
    for t in trns:
        classificar(t)

    jan_jun = [t for t in trns if JAN <= t.data[:7] <= JUN]

    # ---- 1. Fluxo classificado
    entradas = sum(abs(t.valor) for t in jan_jun if t.destino == "entrada")
    despesas = sum(abs(t.valor) for t in jan_jun if t.destino in ("diario", "fixo"))
    sobra = entradas - despesas

    print("=" * 70)
    print("FLUXO CLASSIFICADO (jan..jun)")
    print("=" * 70)
    print(f"  entradas          R$ {brl(entradas):>12}")
    print(f"  despesas          R$ {brl(despesas):>12}")
    print(f"  SOBRA             R$ {brl(sobra):>12}")

    # ---- 2. Caixinha (RDB)
    aplic = sum(abs(t.valor) for t in jan_jun if "aplica" in t.memo.lower() and "rdb" in t.memo.lower())
    resg = sum(abs(t.valor) for t in jan_jun if "resgate rdb" in t.memo.lower())
    delta_caixinha = aplic - resg   # positivo = guardou

    print("\n" + "=" * 70)
    print("CAIXINHA RDB")
    print("=" * 70)
    print(f"  aplicado (guardou)  R$ {brl(aplic):>12}")
    print(f"  resgatado (sacou)   R$ {brl(resg):>12}")
    print(f"  variação líquida    R$ {brl(delta_caixinha):>12}  (negativo = queimou poupança)")

    # ---- 3. Saldos reais dos OFX
    print("\n" + "=" * 70)
    print("SALDOS REAIS (LEDGERBAL dos arquivos)")
    print("=" * 70)
    saldos_cc, saldos_cartao = {}, {}
    for f in sorted(EXTRATOS.glob("*.ofx")):
        txt = f.read_bytes().decode("utf-8", "replace")
        cartao = "<CREDITCARDMSGSRSV1>" in txt
        m = re.search(r"<LEDGERBAL>.*?<BALAMT>(-?[\d.]+).*?<DTASOF>(\d{8})", txt, re.S)
        if not m:
            continue
        val, dt = Decimal(m.group(1)), m.group(2)
        alvo = saldos_cartao if cartao else saldos_cc
        alvo[dt] = val
    for dt, v in sorted(saldos_cc.items()):
        print(f"  conta corrente  {dt[6:8]}/{dt[4:6]}/{dt[:4]}   R$ {brl(v):>10}")
    print()
    for dt, v in sorted(saldos_cartao.items()):
        print(f"  fatura cartão   {dt[6:8]}/{dt[4:6]}/{dt[:4]}   R$ {brl(v):>10}")

    # ---- 4. Dívida do cartão: compras vs pagamentos
    compras = sum(abs(t.valor) for t in jan_jun
                  if t.conta == "cartao" and t.valor < 0)
    pagtos = sum(abs(t.valor) for t in jan_jun
                 if t.conta == "corrente" and "pagamento de fatura" in t.memo.lower())
    print("\n" + "=" * 70)
    print("CARTÃO: COMPRAS x PAGAMENTOS (jan..jun)")
    print("=" * 70)
    print(f"  compras no período   R$ {brl(compras):>12}")
    print(f"  faturas pagas        R$ {brl(pagtos):>12}")
    print(f"  diferença            R$ {brl(compras - pagtos):>12}"
          f"  {'(dívida cresceu)' if compras > pagtos else '(dívida caiu)'}")
    print("\n  obs: parte da diferença é só defasagem — a compra de junho")
    print("       só é paga em julho. Não é necessariamente dívida nova.")

    # ---- 5. Entradas ignoradas (podem ser a explicação)
    print("\n" + "=" * 70)
    print("CRÉDITOS QUE ESTOU IGNORANDO (podem ser renda de verdade)")
    print("=" * 70)
    tot = Decimal(0)
    for t in sorted(jan_jun, key=lambda x: x.data):
        if t.valor > 0 and t.destino == "ignorar" and "rdb" not in t.memo.lower() \
           and "pagamento recebido" not in t.memo.lower():
            tot += t.valor
            print(f"  {t.data}  R$ {brl(t.valor):>10}  {t.memo[:58]}")
    print(f"  TOTAL R$ {brl(tot)}")

    # ---- 6. Fecha?
    print("\n" + "=" * 70)
    print("A CONTA FECHA?")
    print("=" * 70)
    print(f"  sobra classificada             R$ {brl(sobra):>12}")
    print(f"  variação da caixinha           R$ {brl(delta_caixinha):>12}")
    print(f"  defasagem do cartão            R$ {brl(-(compras - pagtos)):>12}")
    residuo = sobra - delta_caixinha + (compras - pagtos)
    print(f"  {'-' * 46}")
    print(f"  resíduo inexplicado           R$ {brl(residuo):>12}")


if __name__ == "__main__":
    main()
