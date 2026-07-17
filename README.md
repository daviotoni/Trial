# Estrutura de um Órgão Público

Modelo de domínio, em Python, para **estudar como um órgão público brasileiro
é estruturado**. Em vez de descrever a organização em texto solto, o projeto
representa cada conceito do Direito Administrativo como um tipo explícito e
navegável: órgão, unidades administrativas, competências, cargos e servidores.

## Conceitos modelados

| Conceito | Classe | O que representa |
|---|---|---|
| Órgão | `Orgao` | Centro de competências e raiz da estrutura |
| Unidade administrativa | `UnidadeAdministrativa` | Subdivisões hierárquicas (secretarias, diretorias, divisões...) |
| Competência | `Competencia` | Atribuição conferida por lei |
| Cargo / Função | `Cargo` | Posição na estrutura (efetivo, comissão, etc.) |
| Servidor | `Servidor` | Pessoa que ocupa um cargo |
| Base legal | `BaseLegal` | Norma que cria ou rege o órgão |

Enumerações auxiliares: `Poder` (Executivo, Legislativo, Judiciário,
Essencial à Justiça), `Esfera` (Federal, Estadual, Distrital, Municipal),
`NaturezaJuridica` (Administração Direta, Autarquia, Fundação...),
`TipoCargo` (efetivo, comissão, função de confiança, eletivo).

## Como rodar

```bash
python main.py          # exibe o órgão de exemplo (Secretaria de Educação)
python -m unittest      # roda os testes
```

## Exemplo de uso

```python
from orgao import Orgao, UnidadeAdministrativa, Cargo, TipoCargo, Esfera, Poder, NaturezaJuridica

orgao = Orgao(
    nome="Secretaria Municipal de Saúde",
    sigla="SMS",
    esfera=Esfera.MUNICIPAL,
    poder=Poder.EXECUTIVO,
    natureza_juridica=NaturezaJuridica.ADMINISTRACAO_DIRETA,
)
gabinete = orgao.definir_topo(UnidadeAdministrativa("Gabinete do Secretário", "GAB"))
gabinete.adicionar_cargo(Cargo("Secretário", TipoCargo.COMISSAO, nivel_hierarquico=5))

diretoria = gabinete.adicionar_subunidade(UnidadeAdministrativa("Diretoria de Atenção Básica", "DAB"))

print(orgao.total_unidades())   # 2
```

## Estrutura do projeto

```
orgao/
  modelos.py      # as classes de domínio (dataclasses, sem dependências)
  visualizar.py   # impressão da árvore e ficha do órgão
  exemplo.py      # monta uma Secretaria de Educação fictícia
  cmdc.py         # estrutura REAL da Câmara Municipal de Duque de Caxias (Lei 3.525/2025)
docs/
  pesquisa-estrutura-cmdc.md  # relatório de pesquisa com fontes verificadas
main.py           # ponto de entrada
tests/            # testes com unittest
```

## Caso real: Câmara Municipal de Duque de Caxias (CMDC)

`orgao/cmdc.py` modela a estrutura administrativa vigente da CMDC conforme a
**Lei nº 3.525/2025**, organizada em quatro graus funcionais (órgãos superiores,
coordenadorias, assessoramento parlamentar e serviços auxiliares):

```bash
python -m orgao.cmdc    # imprime a ficha e o organograma da CMDC
```

O estudo completo — lei, organograma, regime de pessoal (Lei 1.506/2000),
gratificações e o mapa setores → módulos para um futuro sistema de gestão —
está em [`docs/pesquisa-estrutura-cmdc.md`](docs/pesquisa-estrutura-cmdc.md).

> Os números de leis/decretos no exemplo são ilustrativos, apenas para fins de
> estudo da estrutura.
