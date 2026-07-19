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
  seed.sql        # seed gerado (unidades, símbolos, cargos, rubricas, comissões)
  demo.py         # cria o banco e roda consultas de verificação
  legislativo.py  # proposições, sessões, pauta e votações
  comissoes.py    # relatoria e pareceres de comissão (art. 33 do Regimento)
  fluxo.py        # competências legais + ritos configuráveis por tipo de processo
  web/index.html         # interface do sistema (consome a API)
  web/app-standalone.html # versão navegável offline (um arquivo, sem servidor)
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

**Acesso por unidade (setor)**: `POST /login` devolve um token
(`Authorization: Bearer`). O usuário é **lotado numa unidade real** da Lei
3.525/2025 e herda as áreas que aquele setor opera (`unidade_area`) — ex.:
Secretaria-Geral → `PROTOCOLO`, CPL → `COMPRAS`, Recursos Humanos →
`PESSOAL/FOLHA`, e cada um dos **29 gabinetes de vereador** → `LEGISLATIVO`.
`GET /me` devolve a unidade e as áreas do usuário logado (base da
interface por setor). O `ADMIN` (Diretoria-Geral/TI) é superusuário e cria
usuários via `POST /usuarios` (campo `unidade_id`). Um `perfil` legado
serve de compatibilidade quando não há lotação. Senhas com PBKDF2;
primeiro acesso: usuário `admin` com a senha inicial documentada em
`sistema/autenticacao.py` (troque-a). Consultas de transparência ativa
permanecem públicas, por princípio da LAI. Sem login → 401; sem alçada →
403. Demonstração: `python -m sistema.autenticacao`.

**Posse do processo**: encaminhar ou receber um processo é liberado por
**posse — só o setor que detém o processo o remete ao seguinte** (não por
área). Um gabinete não movimenta o processo de outro; o Protocolo autua,
mas cada setor conduz o que está com ele. A trilha de auditoria registra o
login de quem fez cada operação.

**Trava fina por competência (Lei 3.525/2025)**: além da área, atos
legislativos específicos exigem a competência que a lei atribui ao órgão
(`unidade_acao`). Um gabinete opera a área LEGISLATIVO e pode
**APRESENTAR_PROPOSICAO**, mas **não** CONVOCAR_SESSAO nem PAUTAR — esses
atos são da Presidência/Mesa (art. 14) e da Diretoria de Plenário. `GET
/me` traz também as `acoes` do setor. Cada coordenadoria e órgão de 1º grau
carrega sua competência com o artigo correspondente (arts. 11–39), exibida
no painel "Competências do meu setor".

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

`sistema/comissoes.py` completa o rito: as comissões permanentes temáticas
(art. 33 do Regimento Interno) **não se ramificam em setores distintos** —
um **único setor de comissões** recebe todas as matérias e dá
prosseguimento. As comissões temáticas ficam como uma **lista de
classificação**: ao emitir o **parecer** (favorável, com emendas, contrário
ou pela rejeição), o setor **marca** a qual comissão ele corresponde e,
opcionalmente, o relator. Matéria de mérito (PL, PLC, PDL, PR) só entra em
Ordem do Dia com parecer aprovado, **salvo regime de urgência**; o parecer
não vincula o Plenário (parecer contrário, mas aprovado, libera a
deliberação). Demonstração: `python -m sistema.comissoes`. A tramitação
de processos também passou a aceitar **prazo (SLA)** por passagem, com a
consulta `processos_em_atraso` (rota `GET /processos/atrasados`).

`sistema/fluxo.py` é a base de um sistema **interligado entre setores**, em
que cada unidade faz só o que a lei lhe atribui e remete ao setor seguinte:

- **Competências no banco** — a Lei 3.525/2025 traduzida em regra: cada
  unidade tem suas `Competencia` (fonte: `orgao/cmdc.py`) persistidas na
  tabela `competencia`.
- **Ritos configuráveis** — cada `tipo_processo` tem um fluxo em etapas
  (`fluxo_etapa`), e cada etapa é a passagem por uma unidade real, com a
  ação e o prazo (SLA) sugerido. O caminho é **dado, não fixo no código**:
  dá para criar tipos e etapas sem alterar o programa. Vêm semeados dois
  ritos reais — **PL** (Gabinetes → Secretaria-Geral → Consultoria →
  Comissões → Plenário → Redação → Presidência) e **COMPRA** da Lei
  14.133/2021 (Protocolo → Diretoria → Material → Procuradoria → CPL →
  Contratos → Contabilidade → Publicações).
- **Encaminhamento automático** — `tramitar_pelo_fluxo` leva o processo à
  próxima etapa calculando o prazo pela etapa; `proxima_etapa` diz para
  onde ele deve seguir a partir de onde está.

Demonstração: `python -m sistema.fluxo` (imprime os ritos e simula um PL
percorrendo todos os setores). Rotas: `GET /tipos-processo`,
`GET /tipos-processo/{codigo}/etapas`, `GET /unidades/{id}/competencias`,
`POST /processos/{id}/tipo`, `GET /processos/{id}/proxima-etapa`,
`POST /processos/{id}/tramitar-fluxo`. Este é o primeiro passo de uma
evolução em fases rumo ao acesso por unidade (cada setor só o seu) com
trava por competência.

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
