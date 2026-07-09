"""Analisa os OFX (somente leitura, não grava nada) e reporta o que precisa de decisão.

Uso: python scripts/analyze_ofx.py
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

EXTRATOS = Path(__file__).resolve().parent.parent / "extratos"

TRN_RE = re.compile(r"<STMTTRN>(.*?)</STMTTRN>", re.S)
TAG_RE = re.compile(r"<(\w+)>([^<\r\n]*)")
ACCT_RE = re.compile(r"<(?:ACCTID)>([^<\r\n]*)")
PARCELA_RE = re.compile(r"Parcela\s+(\d+)/(\d+)", re.I)


@dataclass
class Trn:
    arquivo: str
    conta: str          # 'corrente' | 'cartao'
    tipo: str           # CREDIT | DEBIT
    data: str           # YYYY-MM-DD
    valor: Decimal
    memo: str
    fitid: str

    @property
    def mes(self) -> str:
        return self.data[:7]


def ler(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def parse(path: Path) -> list[Trn]:
    txt = ler(path)
    conta = "cartao" if "<CREDITCARDMSGSRSV1>" in txt else "corrente"
    out = []
    for bloco in TRN_RE.findall(txt):
        campos = dict(TAG_RE.findall(bloco))
        dt = campos.get("DTPOSTED", "")[:8]
        out.append(
            Trn(
                arquivo=path.name,
                conta=conta,
                tipo=campos.get("TRNTYPE", ""),
                data=f"{dt[:4]}-{dt[4:6]}-{dt[6:8]}",
                valor=Decimal(campos.get("TRNAMT", "0")),
                memo=campos.get("MEMO", "").strip(),
                fitid=campos.get("FITID", "").strip(),
            )
        )
    return out


def main():
    arquivos = sorted(EXTRATOS.glob("*.ofx"))
    if not arquivos:
        sys.exit("Nenhum .ofx encontrado em extratos/")

    todas: list[Trn] = []
    for f in arquivos:
        trns = parse(f)
        todas.extend(trns)
        print(f"{f.name:40} {len(trns):3} transações  [{trns[0].conta}]")

    print("\n" + "=" * 78)
    print("1) FITID É REALMENTE ÚNICO?")
    print("=" * 78)
    por_fitid = defaultdict(list)
    for t in todas:
        por_fitid[t.fitid].append(t)
    colisoes = {k: v for k, v in por_fitid.items() if len(v) > 1}
    print(f"{len(todas)} transações, {len(por_fitid)} FITIDs distintos, "
          f"{len(colisoes)} FITIDs repetidos\n")
    for fit, ts in colisoes.items():
        print(f"  FITID {fit[:13]}... aparece {len(ts)}x:")
        for t in ts:
            print(f"      [{t.conta:8}] {t.data}  {t.valor:>10}  {t.memo[:45]}")
        print()

    print("=" * 78)
    print("2) PAGAMENTO DE FATURA (dupla contagem)")
    print("=" * 78)
    for t in todas:
        if "fatura" in t.memo.lower() or "pagamento recebido" in t.memo.lower():
            print(f"  [{t.conta:8}] {t.data}  {t.valor:>10}  {t.memo}")

    print("\n" + "=" * 78)
    print("3) RESGATE RDB (transferência interna, não é receita)")
    print("=" * 78)
    total_rdb = Decimal(0)
    for t in todas:
        if "resgate rdb" in t.memo.lower():
            total_rdb += t.valor
            print(f"  [{t.conta:8}] {t.data}  {t.valor:>10}  {t.memo}")
    print(f"  --> total que seria contado como ENTRADA por engano: R$ {total_rdb}")

    print("\n" + "=" * 78)
    print("4) COMPRAS PARCELADAS")
    print("=" * 78)
    parcelas = [t for t in todas if PARCELA_RE.search(t.memo)]
    por_compra = defaultdict(list)
    for t in parcelas:
        nome = PARCELA_RE.sub("", t.memo).strip(" -")
        por_compra[nome].append(t)
    total_mes = defaultdict(Decimal)
    for nome, ts in sorted(por_compra.items()):
        ts.sort(key=lambda x: x.data)
        m = PARCELA_RE.search(ts[-1].memo)
        atual, total = int(m.group(1)), int(m.group(2))
        restantes = total - atual
        valor = abs(ts[-1].valor)
        print(f"  {nome[:32]:32} R$ {valor:>7} x  parcela {atual}/{total}"
              f"  -> faltam {restantes} (R$ {valor * restantes})")
        for t in ts:
            total_mes[t.mes] += abs(t.valor)
    print()
    for mes, v in sorted(total_mes.items()):
        print(f"  parcelas em {mes}: R$ {v}")

    print("\n" + "=" * 78)
    print("5) ENTRADAS (CREDIT) — precisam da sua decisão")
    print("=" * 78)
    for t in sorted(todas, key=lambda x: x.data):
        if t.valor > 0:
            print(f"  [{t.conta:8}] {t.data}  {t.valor:>10}  {t.memo[:60]}")

    print("\n" + "=" * 78)
    print("6) RECORRENTES (mesmo memo em junho E julho) — candidatos a GASTO FIXO")
    print("=" * 78)
    por_memo = defaultdict(list)
    for t in todas:
        if t.valor < 0 and not PARCELA_RE.search(t.memo):
            chave = re.sub(r"\s*-\s*•.*$", "", t.memo)[:30]
            por_memo[chave].append(t)
    for memo, ts in sorted(por_memo.items()):
        meses = {t.mes for t in ts}
        if len(meses) > 1:
            vals = ", ".join(f"{t.data}: R$ {abs(t.valor)}" for t in sorted(ts, key=lambda x: x.data))
            print(f"  {memo:32} {vals}")


if __name__ == "__main__":
    main()
