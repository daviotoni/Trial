# Plano — Módulo do Protocolo (Coordenadoria da Secretaria-Geral)

Base legal: **Lei nº 3.525/2025, art. 37** — protocolo-geral, autuação,
numeração e tramitação de processos administrativos e legislativos. O
Protocolo é a porta de entrada e o eixo da tramitação.

## Estado inicial

- Autuação (tipo, assunto, unidade de origem, data) com numeração
  sequencial por ano; consulta **só pelo id interno**; tramitação.
- Backend já existente e ocioso na tela: `processos_em_atraso` (SLA),
  mudanças de situação (arquivar/concluir/desarquivar),
  `receber_tramitacao`, tabela `documento`.

## Blocos

| Bloco | Escopo |
|---|---|
| **P1. Busca e consulta** | Filtros (número, ano, tipo, situação, interessado, assunto), localização atual, abrir detalhe a partir da lista |
| **P2. Interessado e documentos** | Interessado na autuação; juntada de documentos (ofício, parecer, despacho, anexo) e listagem no detalhe |
| **P3. Painel e recebimento** | Painel do protocolo (recém-autuados, em atraso, por situação); confirmação de recebimento de tramitação |

Sem mudança de schema: `processo.interessado` e a tabela `documento` já
existem. Alçada: área **PROTOCOLO** (Coordenadoria da Secretaria-Geral);
a consulta de processos é pública por transparência (LAI).

## Entrada única: o Protocolo autua e numera tudo (art. 37)

Todo processo nasce no Protocolo. A autuação e a numeração são atos
privativos do Protocolo — nenhum setor numera ou autua por conta própria.

- **Proposições dos gabinetes**: o gabinete **apresenta** (situação
  `APRESENTADA`, sem número); a proposição entra na fila do Protocolo, que
  a **autua** (numera, abre o processo com origem no Protocolo, vincula o
  rito) e dá o **andamento inicial** ao setor seguinte. Funções:
  `apresentar_rascunho`, `proposicoes_apresentadas`, `autuar_proposicao`.
- **Compras/Licitações**: a contratação é autuada com o processo nascendo
  no Protocolo; o setor demandante fica como interessado.
- **Processos administrativos**: autuados diretamente pelo Protocolo, como
  já era.
