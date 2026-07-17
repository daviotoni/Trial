"""Modelos de domínio da estrutura de um órgão público.

A modelagem segue conceitos do Direito Administrativo brasileiro:

- **Órgão**: centro de competências integrante da estrutura de uma pessoa
  jurídica (a Administração). Não tem personalidade jurídica própria — quem
  a possui é o ente (União, Estado, Município) ou a entidade da
  Administração Indireta (autarquia, fundação etc.).
- **Unidade administrativa**: as subdivisões internas do órgão
  (secretarias, departamentos, coordenações, divisões, setores), organizadas
  hierarquicamente.
- **Competência**: a atribuição conferida por lei ao órgão/unidade.
- **Cargo** e **Servidor**: o elemento humano que ocupa a estrutura.

Todas as classes usam `dataclasses` da biblioteca padrão, sem dependências
externas, para manter o estudo simples de rodar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterator, Optional


class Poder(Enum):
    """Poder da República ao qual o órgão está vinculado."""

    EXECUTIVO = "Executivo"
    LEGISLATIVO = "Legislativo"
    JUDICIARIO = "Judiciário"
    # Funções essenciais à Justiça e órgãos autônomos (MP, TCU, Defensoria).
    ESSENCIAL_A_JUSTICA = "Essencial à Justiça"


class Esfera(Enum):
    """Esfera federativa (art. 18 da Constituição Federal)."""

    FEDERAL = "Federal"
    ESTADUAL = "Estadual"
    DISTRITAL = "Distrital"
    MUNICIPAL = "Municipal"


class NaturezaJuridica(Enum):
    """Natureza jurídica da entidade a que o órgão pertence.

    Administração Direta são órgãos sem personalidade própria (ministérios,
    secretarias). A Administração Indireta reúne entidades com personalidade
    jurídica própria (autarquias, fundações, empresas públicas e sociedades
    de economia mista), nos termos do Decreto-Lei 200/1967.
    """

    ADMINISTRACAO_DIRETA = "Administração Direta"
    AUTARQUIA = "Autarquia"
    FUNDACAO_PUBLICA = "Fundação Pública"
    EMPRESA_PUBLICA = "Empresa Pública"
    SOCIEDADE_ECONOMIA_MISTA = "Sociedade de Economia Mista"


class TipoCargo(Enum):
    """Classificação básica de um cargo/função na estrutura."""

    EFETIVO = "Cargo efetivo"          # provido por concurso público
    COMISSAO = "Cargo em comissão"     # de livre nomeação e exoneração
    FUNCAO_CONFIANCA = "Função de confiança"
    ELETIVO = "Cargo eletivo"


@dataclass(frozen=True)
class BaseLegal:
    """Referência normativa que cria ou rege o órgão/competência.

    Exemplos: "Lei nº 13.844/2019", "Decreto nº 9.680/2019", "art. 37, CF".
    """

    especie: str          # "Lei", "Decreto", "Constituição", "Portaria"...
    numero: str           # "13.844/2019", "art. 37"
    ementa: str = ""      # resumo do que a norma dispõe

    def __str__(self) -> str:
        base = f"{self.especie} {self.numero}".strip()
        return f"{base} — {self.ementa}" if self.ementa else base


@dataclass(frozen=True)
class Competencia:
    """Atribuição legal conferida a um órgão ou unidade administrativa."""

    descricao: str
    base_legal: Optional[BaseLegal] = None

    def __str__(self) -> str:
        if self.base_legal:
            return f"{self.descricao} ({self.base_legal})"
        return self.descricao


@dataclass
class Servidor:
    """Pessoa física que ocupa um cargo na estrutura."""

    nome: str
    matricula: str = ""


@dataclass
class Cargo:
    """Cargo ou função existente na estrutura do órgão."""

    denominacao: str
    tipo: TipoCargo
    # Nível de direção/chefia (0 = sem chefia; quanto maior, mais alto).
    nivel_hierarquico: int = 0
    ocupante: Optional[Servidor] = None

    @property
    def vago(self) -> bool:
        return self.ocupante is None

    def __str__(self) -> str:
        status = "vago" if self.vago else self.ocupante.nome  # type: ignore[union-attr]
        return f"{self.denominacao} [{self.tipo.value}] — {status}"


@dataclass
class UnidadeAdministrativa:
    """Subdivisão interna do órgão, organizada de forma hierárquica.

    Uma unidade pode conter outras (subunidades), formando a árvore
    organizacional. Cada unidade tem competências próprias e cargos.
    """

    nome: str
    sigla: str = ""
    competencias: list[Competencia] = field(default_factory=list)
    cargos: list[Cargo] = field(default_factory=list)
    subunidades: list["UnidadeAdministrativa"] = field(default_factory=list)

    def adicionar_subunidade(self, unidade: "UnidadeAdministrativa") -> "UnidadeAdministrativa":
        """Anexa uma subunidade e a devolve (permite encadear)."""
        self.subunidades.append(unidade)
        return unidade

    def adicionar_cargo(self, cargo: Cargo) -> Cargo:
        self.cargos.append(cargo)
        return cargo

    def adicionar_competencia(self, competencia: Competencia) -> Competencia:
        self.competencias.append(competencia)
        return competencia

    def percorrer(self, nivel: int = 0) -> Iterator[tuple[int, "UnidadeAdministrativa"]]:
        """Percorre a árvore em profundidade, gerando (nível, unidade)."""
        yield nivel, self
        for sub in self.subunidades:
            yield from sub.percorrer(nivel + 1)

    def contar_unidades(self) -> int:
        """Total de unidades nesta subárvore, incluindo a própria."""
        return sum(1 for _ in self.percorrer())

    def contar_cargos(self) -> int:
        """Total de cargos em toda a subárvore."""
        return sum(len(u.cargos) for _, u in self.percorrer())

    def cargos_vagos(self) -> list[Cargo]:
        """Lista todos os cargos vagos na subárvore."""
        return [c for _, u in self.percorrer() for c in u.cargos if c.vago]

    def __str__(self) -> str:
        return f"{self.nome} ({self.sigla})" if self.sigla else self.nome


@dataclass
class Orgao:
    """Órgão público — a raiz da estrutura.

    Reúne a identificação institucional (nome, sigla, esfera, poder,
    natureza jurídica), a base legal de criação e a unidade administrativa
    de topo (o gabinete/direção máxima), a partir da qual pende toda a
    hierarquia.
    """

    nome: str
    sigla: str
    esfera: Esfera
    poder: Poder
    natureza_juridica: NaturezaJuridica
    base_legal_criacao: Optional[BaseLegal] = None
    finalidade: str = ""
    unidade_topo: Optional[UnidadeAdministrativa] = None

    def definir_topo(self, unidade: UnidadeAdministrativa) -> UnidadeAdministrativa:
        self.unidade_topo = unidade
        return unidade

    def percorrer(self) -> Iterator[tuple[int, UnidadeAdministrativa]]:
        """Percorre toda a estrutura a partir da unidade de topo."""
        if self.unidade_topo is not None:
            yield from self.unidade_topo.percorrer()

    def total_unidades(self) -> int:
        return self.unidade_topo.contar_unidades() if self.unidade_topo else 0

    def total_cargos(self) -> int:
        return self.unidade_topo.contar_cargos() if self.unidade_topo else 0

    def cargos_vagos(self) -> list[Cargo]:
        return self.unidade_topo.cargos_vagos() if self.unidade_topo else []

    def __str__(self) -> str:
        return f"{self.nome} ({self.sigla}) — {self.esfera.value}/{self.poder.value}"
