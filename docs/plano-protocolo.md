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
