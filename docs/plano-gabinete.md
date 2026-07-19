# Plano — Módulo do Gabinete (produção legislativa)

Planejamento do conjunto de funcionalidades do setor **gabinete de
vereador**, fundamentado no **Regimento Interno** (Resolução nº 1.835/2000,
arts. 87–115) e na **Lei nº 3.525/2025** (art. 1º, p.u., e art. 79 —
gabinetes como unidades de assessoramento ao mandato).

## Decisões do gestor (registradas)

1. **Acesso somente do vereador**: cada gabinete tem **um único login, do
   vereador titular**. Assessores não recebem login por ora (papéis
   internos de gabinete ficam para o futuro).
2. **Ordem de implementação**: começar pelo **Bloco 1** (catálogo completo
   de proposições + rascunho + justificativa), fundação dos demais.
3. **Apoiamento/assinaturas**: colhidas **em papel** por enquanto — o
   sistema não controla assinaturas nesta fase. Assinatura digital de
   coautoria/apoiamento é **fase futura**.

## Blocos planejados

| Bloco | Escopo | Base regimental |
|---|---|---|
| **1. Catálogo + rascunho** *(primeiro)* | Todos os tipos de proposição, campos corretos, rascunho antes de protocolar, autor automático | arts. 87, 88 §4º, 92 |
| 2. Coautoria + apoiamento | Subscrição por outros gabinetes, mínimos por tipo | art. 88 §§2º–6º |
| 3. Emendas a matéria alheia | Emenda/substitutivo com pertinência | arts. 114–115, 88 VIII |
| 4. Acompanhamento rico | Pareceres, prazos, alertas de arquivamento, requerimentos derivados (retirada, inclusão em pauta, desarquivamento) | arts. 90, 93–95, 107–113 |

## Bloco 1 — detalhamento

### Tipos de proposição (art. 87, §1º + arts. 96–106)

- **PELO** — Proposta de Emenda à Lei Orgânica *(novo)*
- **PLC** — Projeto de Lei Complementar à Lei Orgânica
- **PL** — Projeto de Lei
- **PR** — Projeto de Resolução (art. 100)
- **PDL** — Projeto de Decreto Legislativo (art. 99)
- **Indicação**, com **subtipo**: *simples* (encaminhada pelo Presidente ao
  Executivo, art. 102) ou *legislativa* (vai à Comissão de Justiça,
  art. 103)
- **Moção**, com **subtipo**: aplauso, pesar, repúdio, congratulações,
  desaprovação (arts. 105–106)
- **Requerimento**, com **espécie** (art. 107): despacho do Presidente ×
  deliberação do Plenário
- (Emenda e Recurso entram nos Blocos 3/4.)

### Modelo de dados (mudanças planejadas)

- `proposicao`: novos campos `subtipo` (opcional), `texto` (articulado,
  art. 92), `justificativa` (obrigatória, art. 88 §4º), `regime`
  (ORDINARIA / PRIORIDADE / ESPECIAL / URGENCIA — art. 91; padrão
  ORDINARIA) e situação **RASCUNHO**.
- **Rascunho não recebe número**: a numeração sequencial só ocorre no
  protocolo (evita queimar números). Rascunho é visível apenas ao gabinete
  autor.
- **Seed da 20ª Legislatura**: criar os 29 parlamentares reais e seus
  mandatos ligados aos respectivos gabinetes (`mandato.gabinete_unidade_id`
  já existe). O login do gabinete passa a identificar o vereador → autor
  automático das proposições.

### Regras de validação (art. 88, preventivo no gabinete)

- Ementa obrigatória; justificativa obrigatória; texto obrigatório para
  projetos (PL/PLC/PDL/PR/PELO).
- Checklist de admissibilidade como **aviso** (não bloqueio): matéria
  estranha à ementa, expressões ofensivas, duplicidade — o juízo formal de
  recusa é da Presidência (art. 88, §1º; competência do Presidente de
  receber ou recusar), etapa que pertence ao Bloco 4.

### Telas (login do vereador)

1. **Nova proposição** (evolui a atual): catálogo completo com descrição
   de cada tipo, subtipo quando aplicável, ementa, texto, justificativa;
   botões **Salvar rascunho** e **Protocolar**.
2. **Rascunhos**: listar, editar, excluir, protocolar.
3. **Minhas proposições**: segue como acompanhamento pós-protocolo.

### Critérios de aceite

- Vereador cria rascunho de PL sem número; protocola e recebe
  "PL n/ano" com processo autuado no gabinete e rito vinculado.
- Indicação simples e legislativa distinguidas; moção com subtipo.
- Proposição protocolada tem autor = vereador titular do gabinete,
  automaticamente.
- Justificativa ausente bloqueia o protocolo (não o rascunho).
- Nada disso aparece para logins de outros setores.

## Fora de escopo nesta fase (anotado para o futuro)

- Assinatura digital de coautoria/apoiamento, com mínimos por tipo
  (art. 88 §6º: CPI e urgência = 1/3; votação secreta; títulos
  honoríficos = 1/3; moção de desaprovação = 1/3 etc.).
- Logins de assessores com papéis internos (redator × signatário).
- Recusa formal pela Presidência com recurso à CLJRF (art. 88 §1º).
- Regras de fim de legislatura (art. 95) e vedação do art. 94.
