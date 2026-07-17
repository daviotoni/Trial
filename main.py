"""Ponto de entrada: exibe a estrutura do órgão de exemplo.

Execute:

    python main.py
"""

from orgao.exemplo import construir_secretaria_educacao
from orgao.visualizar import detalhar_competencias, ficha_orgao


def main() -> None:
    orgao = construir_secretaria_educacao()
    print(ficha_orgao(orgao))
    print()
    print("DETALHAMENTO POR UNIDADE")
    print("-" * 68)
    print(detalhar_competencias(orgao))

    vagos = orgao.cargos_vagos()
    if vagos:
        print()
        print(f"CARGOS VAGOS ({len(vagos)})")
        print("-" * 68)
        for cargo in vagos:
            print(f"  - {cargo.denominacao} [{cargo.tipo.value}]")


if __name__ == "__main__":
    main()
