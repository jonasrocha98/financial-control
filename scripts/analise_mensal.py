"""Análise mensal dos extratos: custo de vida, parcelas, e ponto de equilíbrio.

Somente leitura. Não toca no banco.
Uso: python scripts/analise_mensal.py
"""
from __future__ import annotations

import io
import re
import statistics
import sys
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ofx_to_planilha import EXTRATOS, PARCELA_RE, Trn, classificar, parse  # noqa: E402


def brl(v) -> str:
    v = Decimal(str(v)).quantize(Decimal("0.01"), ROUND_HALF_UP)
    i, _, c = f"{v:,.2f}".partition(".")
    return f"{i.replace(',', '.')},{c}"


def med(vals: list[Decimal]) -> Decimal:
    if not vals:
        return Decimal(0)
    return Decimal(str(statistics.median([float(v) for v in vals]))).quantize(Decimal("0.01"))


def main():
    trns: list[Trn] = []
    for f in sorted(EXTRATOS.glob("*.ofx")):
        trns.extend(parse(f))
    for t in trns:
        classificar(t)

    # Meses utilizáveis: precisam ter dados de conta corrente (receita) e cartão
    contas_por_mes = defaultdict(set)
    for t in trns:
        contas_por_mes[t.data[:7]].add(t.conta)
    completos = sorted(m for m, c in contas_por_mes.items() if {"corrente", "cartao"} <= c)
    # julho está em curso -> fora da mediana
    fechados = [m for m in completos if m < "2026-07"]

    print("=" * 74)
    print("MESES USADOS NA MEDIANA:", ", ".join(fechados))
    excluidos = sorted(set(contas_por_mes) - set(fechados))
    print("EXCLUÍDOS:", ", ".join(excluidos), "(incompletos ou em curso)")
    print("=" * 74)

    # ---------------------------------------------------------- agregação mensal
    linhas = {}
    for m in sorted(contas_por_mes):
        ent = rec = parc = fix = resg = Decimal(0)
        for t in trns:
            if t.data[:7] != m:
                continue
            v = abs(t.valor)
            if t.destino == "entrada":
                ent += v
            elif t.destino == "fixo":
                fix += v
            elif t.destino == "diario":
                if PARCELA_RE.search(t.memo):
                    parc += v
                else:
                    rec += v
            elif "resgate rdb" in t.memo.lower():
                resg += v
        linhas[m] = dict(entradas=ent, recorrente=rec, parcelas=parc,
                         fixos=fix, resgates=resg,
                         custo=fix + rec + parc, sobra=ent - fix - rec - parc)

    print()
    hdr = f"{'mês':9} {'entradas':>11} {'fixos':>9} {'recorrente':>11} {'parcelas':>10} {'sobra':>11} {'caixinha':>10}"
    print(hdr)
    print("-" * len(hdr))
    for m in sorted(linhas):
        d = linhas[m]
        marca = "" if m in fechados else "  *"
        print(f"{m:9} {brl(d['entradas']):>11} {brl(d['fixos']):>9} {brl(d['recorrente']):>11} "
              f"{brl(d['parcelas']):>10} {brl(d['sobra']):>11} {brl(d['resgates']):>10}{marca}")
    print("\n  * mês incompleto — fora dos cálculos")

    # ---------------------------------------------------------------- medianas
    # ATENÇÃO: mediana NÃO é aditiva. mediana(A) - mediana(B) != mediana(A-B).
    # Por isso cada agregado é medianado sobre o TOTAL MENSAL, não sobre partes.
    ent = med([linhas[m]["entradas"] for m in fechados])
    custo_vida = med([linhas[m]["fixos"] + linhas[m]["recorrente"] for m in fechados])
    custo_total = med([linhas[m]["custo"] for m in fechados])
    sobra_mediana = med([linhas[m]["sobra"] for m in fechados])
    parc = med([linhas[m]["parcelas"] for m in fechados])

    print("\n" + "=" * 74)
    print("MEDIANA DOS MESES FECHADOS (medianada sobre o total de cada mês)")
    print("=" * 74)
    print(f"  Entradas (renda)                     R$ {brl(ent):>10}")
    print(f"  Parcelas (temporário)                R$ {brl(parc):>10}")
    print()
    print(f"  >> CUSTO DE VIDA (fixo+recorrente)   R$ {brl(custo_vida):>10}   <- persiste")
    print(f"  >> Custo total de hoje (+parcelas)   R$ {brl(custo_total):>10}")
    print(f"  >> SOBRA MEDIANA (mês típico)        R$ {brl(sobra_mediana):>10}")
    media_sobra = sum(linhas[m]["sobra"] for m in fechados) / len(fechados)
    print(f"  >> sobra média (para déficit acumulado) R$ {brl(media_sobra):>8}")

    # ------------------------------------------------------ ponto de equilíbrio
    print("\n" + "=" * 74)
    print("QUANTO PRECISO FATURAR")
    print("=" * 74)
    gap_hoje = custo_total - ent
    gap_pos = custo_vida - ent
    print(f"  Ponto de equilíbrio hoje (com parcelas)   R$ {brl(custo_total):>10}")
    print(f"    sua renda mediana                       R$ {brl(ent):>10}")
    print(f"    FALTA                                   R$ {brl(gap_hoje):>10}")
    print()
    print(f"  Quando as parcelas acabarem               R$ {brl(custo_vida):>10}")
    print(f"    FALTA                                   R$ {brl(gap_pos):>10}")

    print("\n  Com investimento (gross-up sobre o custo de vida):")
    for p in (5, 10, 15, 20):
        alvo = (custo_vida / (Decimal(1) - Decimal(p) / 100)).quantize(Decimal("0.01"))
        print(f"    {p:>2}%  ->  faturar R$ {brl(alvo):>10}   (falta R$ {brl(alvo - ent)})")

    # --------------------------------------------------------------- caixinha
    print("\n" + "=" * 74)
    print("CAIXINHA RDB — fluxo líquido")
    print("=" * 74)
    tot_ap = tot_rs = Decimal(0)
    for m in fechados:
        ap = sum(abs(t.valor) for t in trns
                 if t.data[:7] == m and re.search(r"aplica..o rdb", t.memo, re.I))
        rs = sum(abs(t.valor) for t in trns
                 if t.data[:7] == m and re.search(r"resgate rdb", t.memo, re.I))
        tot_ap += ap
        tot_rs += rs
        if ap or rs:
            print(f"  {m}:  guardou R$ {brl(ap):>9}   sacou R$ {brl(rs):>9}   "
                  f"líquido R$ {brl(ap - rs):>10}")
    liq = tot_ap - tot_rs
    print(f"  {'-' * 66}")
    print(f"  TOTAL:  guardou R$ {brl(tot_ap):>9}   sacou R$ {brl(tot_rs):>9}   "
          f"líquido R$ {brl(liq):>10}")
    print(f"\n  Poupança consumida em {len(fechados)} meses: R$ {brl(-liq)}"
          f"  (R$ {brl(-liq / len(fechados))}/mês)")

    # --------------------------------------------------------------- parcelas
    print("\n" + "=" * 74)
    print("PARCELAS — CRONOGRAMA E ALÍVIO FUTURO")
    print("=" * 74)
    compras = defaultdict(list)
    for t in trns:
        m = PARCELA_RE.search(t.memo)
        if m:
            nome = PARCELA_RE.sub("", t.memo).strip(" -")
            compras[nome].append((t.data, int(m.group(1)), int(m.group(2)), abs(t.valor)))

    ativas = []
    for nome, itens in sorted(compras.items()):
        itens.sort()
        data, atual, total, valor = itens[-1]
        restantes = total - atual
        if restantes > 0:
            ativas.append((nome, valor, restantes, atual, total))
        estado = f"faltam {restantes}" if restantes else "QUITADA"
        print(f"  {nome[:30]:32} R$ {brl(valor):>8}/mês  {atual}/{total}  {estado}")

    if ativas:
        print("\n  Alívio mensal conforme cada uma termina:")
        alivio = defaultdict(Decimal)
        for nome, valor, restantes, atual, total in ativas:
            alivio[restantes] += valor
        acumulado = Decimal(0)
        comprometido = sum(v for _, v, _, _, _ in ativas)
        print(f"    hoje: R$ {brl(comprometido)}/mês comprometidos")
        for meses in sorted(alivio):
            acumulado += alivio[meses]
            print(f"    em {meses} mês(es): libera +R$ {brl(alivio[meses])}/mês "
                  f"(acumulado R$ {brl(acumulado)})")
        total_devido = sum(v * r for _, v, r, _, _ in ativas)
        print(f"    dívida total restante: R$ {brl(total_devido)}")

    # --------------------------------------------------- memos não reconhecidos
    print("\n" + "=" * 74)
    print("NÃO RECONHECIDOS (precisam de regra ou da sua revisão)")
    print("=" * 74)
    baixa = defaultdict(lambda: [0, Decimal(0)])
    for t in trns:
        if t.confianca == "BAIXA":
            chave = re.sub(r"\s*-\s*•.*$", "", t.memo)[:38]
            baixa[chave][0] += 1
            baixa[chave][1] += abs(t.valor)
    for memo, (n, v) in sorted(baixa.items(), key=lambda x: -x[1][1]):
        print(f"  {n:>3}x  R$ {brl(v):>10}  {memo}")
    print(f"\n  {sum(n for n, _ in baixa.values())} linhas em amarelo na planilha")


if __name__ == "__main__":
    main()
