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
  cmdc.py         # estrutura REAL da CMDC (Lei 3.525/2025) + Anexo I completo
sistema/
  schema.sql      # banco do sistema de gestão (SQL portável: SQLite/PostgreSQL)
  gerar_seed.py   # carga inicial gerada a partir de orgao/cmdc.py
  seed.sql        # seed gerado (unidades, símbolos, cargos, rubricas)
  demo.py         # cria o banco e roda consultas de verificação
docs/
  pesquisa-estrutura-cmdc.md      # relatório de pesquisa com fontes verificadas
  modelo-de-dados.md              # desenho do banco: módulos, entidades, regras
  lei-3525-2025-texto-integral.txt
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

## Sistema de gestão (protótipo do banco)

O diretório `sistema/` contém o modelo de dados do sistema que atenderá todos
os setores da Casa (7 módulos: estrutura, pessoal, folha, protocolo,
legislativo, compras e controle/transparência), documentado em
[`docs/modelo-de-dados.md`](docs/modelo-de-dados.md):

```bash
python -m sistema.demo      # cria o banco (SQLite) com schema + seed e verifica
python -m sistema.cenario   # estudo de caso: nomeações, tramitação e folha
python -m sistema.api       # API REST em http://127.0.0.1:8000 (banco cmdc.db)
python -m sistema.gerar_seed > sistema/seed.sql   # regenera a carga inicial
```

A API (`sistema/api.py`, biblioteca padrão, sem dependências) expõe
organograma, unidades, cargos com vagas disponíveis, servidores, nomeações,
processos/tramitações, plenário e cálculo de folha — e serve em `/` a
**interface web** (`sistema/web/index.html`, HTML/JS puro): organograma
navegável, quadro do Anexo I com filtro, autuação/consulta/tramitação de
processos e placar de votações nominais. Basta abrir
`http://127.0.0.1:8000` com a API no ar. Violações de regra legal retornam
HTTP 422 com a mensagem e o artigo:

```bash
curl -X POST localhost:8000/folhas -d '{"competencia":"2025-09","percentual_gal":200}'
# {"erro": "GAL acima do teto de 150% (art. 7º)"}
```

`sistema/servicos.py` implementa as regras de negócio: nomeações que respeitam
as vagas do Anexo I e os requisitos de função de confiança (efetivo com 2 anos,
art. 5º, §3º), protocolo com numeração sequencial, tramitação encadeada e o
cálculo de folha com as gratificações da lei (GAL com teto de 150%, GRAT-CC de
100% para efetivo em comissão, GRAT-COM de 40%, REP-TL, GAP, REP-JUD).

`sistema/legislativo.py` cobre a atividade-fim: proposições numeradas por
tipo/ano com autuação automática no protocolo, sessões, ordem do dia e
votações **nominais** (voto individual, apuração por maioria simples) ou
simbólicas — com bloqueios para matéria fora de pauta ou já votada, e
**maioria absoluta** para PLC (art. 178 do Regimento Interno).
Demonstração: `python -m sistema.legislativo`.

`sistema/compras.py` implementa o fluxo da Lei 14.133/2021: abertura de
contratação com autuação automática, limites de dispensa do art. 75,
homologação obrigatória antes do contrato, empenhos que não excedem o valor
contratado e trilha de auditoria em toda operação. `sistema/transparencia.py`
fecha o ciclo: registro de publicações, **pendências de publicação**
(contratos/folhas ainda não divulgados), trilha de auditoria consultável e o
painel de indicadores exibido na primeira aba da interface web.

A carga inicial é derivada de `orgao/cmdc.py` — as 49 unidades e as 615 vagas
do Anexo I da Lei 3.525/2025 entram no banco sem digitação manual.

> Os números de leis/decretos no exemplo são ilustrativos, apenas para fins de
> estudo da estrutura.
