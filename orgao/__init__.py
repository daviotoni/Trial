"""Modelo de domínio para a estrutura de um órgão público brasileiro.

Este pacote representa, em código, como um órgão público é organizado:
a natureza jurídica, a esfera e o poder a que pertence, sua base legal de
criação, a hierarquia de unidades administrativas, os cargos e as
competências (atribuições legais).

O objetivo é didático: permitir "estudar a estrutura de um órgão"
navegando por um modelo tipado e explícito, em vez de um texto solto.
"""

from orgao.modelos import (
    Cargo,
    Competencia,
    Esfera,
    NaturezaJuridica,
    Orgao,
    Poder,
    Servidor,
    TipoCargo,
    UnidadeAdministrativa,
)

__all__ = [
    "Cargo",
    "Competencia",
    "Esfera",
    "NaturezaJuridica",
    "Orgao",
    "Poder",
    "Servidor",
    "TipoCargo",
    "UnidadeAdministrativa",
]

__version__ = "0.1.0"
