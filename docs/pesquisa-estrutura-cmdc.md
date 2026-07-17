# Estrutura Administrativa da Câmara Municipal de Duque de Caxias (CMDC)

**Relatório de pesquisa para fundamentar o desenho de um sistema de gestão que atenda todos os setores da Casa.**

> Metodologia: pesquisa em 5 frentes (norma-base, organograma/transparência, cargos/pessoal,
> Regimento/Lei Orgânica, processos e sistemas), 13 fontes coletadas, 37 afirmações extraídas,
> 25 submetidas a verificação adversarial (3 votos independentes cada): **23 confirmadas**,
> 1 refutada, 1 não verificada. Data da pesquisa: 17/07/2026.

---

## 1. A base normativa obrigatória: Lei nº 3.525, de 29/08/2025

Ementa: *"Dispõe sobre a organização administrativa da Câmara Municipal de Duque de Caxias,
e dá outras providências."* ([texto oficial no site da CMDC](https://www.cmdc.rj.gov.br/?p=30397))

O art. 1º declara que a lei **reformula a estrutura administrativa e organizacional da CMDC**,
incluindo unidades administrativas e atribuições gerais e específicas. É, portanto, a norma
vigente que define os setores que o sistema precisa atender.

Pontos estruturais da lei:

- **Presidência e Mesa Diretora** exercem *comando político-institucional* e **não integram a
  hierarquia técnico-administrativa** (art. 2º, parágrafo único).
- A **Diretoria-Geral** é o *órgão central de apoio administrativo*, **diretamente subordinada
  à Presidência** (art. 15).
- Cargos comissionados (quantitativos, denominações, lotações e remunerações) e funções
  gratificadas constam do **Anexo I** (art. 3º, §1º e art. 5º, §1º) — *os anexos não estão
  reproduzidos na publicação online; é preciso obtê-los na íntegra junto à CMDC*.
- A Mesa Diretora pode transformar, extinguir ou remanejar cargos comissionados sem aumento
  de despesa (art. 3º, §5º).
- Órgãos de 3º grau são lotados nos Gabinetes de Vereadores e da Mesa, com provimento por
  indicação dos titulares (art. 3º, §2º).

### 1.1 Estrutura em quatro graus funcionais

**1º grau — Órgãos Superiores de Direção e Assessoramento Técnico (9):**

1. Consultoria-Geral Legislativa
2. Controladoria-Geral
3. Diretoria da Escola do Legislativo
4. Diretoria de Plenário
5. Diretoria-Geral
6. Ouvidoria-Geral
7. Procuradoria-Geral
8. Superintendência-Geral
9. Superintendência de Assuntos Estratégicos

**2º grau — Órgãos de Coordenação Técnico-Administrativa (20):**

| Área-fim (legislativo) | Área-meio (administração) |
|---|---|
| Coordenadoria de Apoio Legislativo | Coordenadoria de Avaliação e Acompanhamento de Compras |
| Coordenadoria de Assuntos de Plenário | Coordenadoria de Contabilidade |
| Coordenadoria de Atas e Projetos | Coordenadoria de Finanças |
| Coordenadoria de Redação Oficial e Legislativa | Coordenadoria de Licitações e Contratos |
| Coordenadoria de Documentação Histórica | Coordenadoria de Manutenção |
| Coordenadoria de Publicações e Transparência | Coordenadoria de Material |
| Coordenadoria da Secretaria-Geral | Coordenadoria de Patrimônio |
| Coordenadoria de Cerimonial e Comunicação Social | Coordenadoria de Recursos Humanos |
| Coordenadoria de Polícia Legislativa | Coordenadoria de Tecnologia da Informação e Comunicação |
| Coordenadoria de Prevenção a Incêndio | Diretoria Administrativa |

**3º grau — Órgãos de Assessoramento Parlamentar:** Assessoria de Gabinete Parlamentar,
Assessoria Especial da Presidência, Assessores Parlamentares e Assistência às Comissões
Permanentes — lotados nos gabinetes de vereadores e lideranças.

**4º grau — Serviços Auxiliares:** Departamento do e-Social, copa, manutenção predial,
telefonia, reprografia, limpeza, transporte e vigilância patrimonial.

### 1.2 Gratificações e adicionais (regras que o módulo de folha precisa implementar)

| Dispositivo | Verba | Beneficiário | Percentual sobre vencimento básico |
|---|---|---|---|
| Art. 7º | Gratificação de Atividade Legislativa (GAL) | Efetivos e comissionados | até **150%** |
| Art. 8º | Adicional de Representação | Carreira de Técnico Legislativo | **60%** |
| Art. 9º | Gratificação de Atividade Perigosa (GAP) | Inspetor de Segurança do Legislativo | **40%** |
| Art. 10 | Adicional de Representação Judiciária | Consultor Jurídico | **40%** |
| Art. 46, §2º | Gratificação de Comissão | Membros de comissões e agentes de contratação | **40%** |

Critérios específicos da GAL serão definidos em Resolução posterior (art. 7º, parágrafo único).

---

## 2. Organograma oficial anterior (2023) — útil para migração e histórico

O [organograma publicado pela CMDC em 30/10/2023](https://www.cmdc.rj.gov.br/wp-content/uploads/2023/10/organograma_30_10_2023_14_40.pdf)
(anterior à Lei 3.525/2025) mostrava:

- **Mesa Diretora** no topo, com 7 unidades diretamente subordinadas: Gabinetes de Vereadores,
  Defensoria do Povo, Coordenadoria Militar, Controladoria-Geral, Diretoria-Geral,
  Coordenadoria de Segurança Legislativa e Consultoria-Geral Jurídica.
- **Diretoria-Geral** como órgão de direção executiva (planeja, supervisiona e controla todos
  os serviços, ordena despesas, promove compras), tendo sob si: Diretoria de Plenário,
  Diretoria Administrativa, Coordenadoria de Avaliação e Acompanhamento de Compras,
  Coordenadoria de Licitação, Assessoria de Cerimonial e Comunicação Social e Diretoria de
  Orçamento, Finanças e Contabilidade.
- **Controladoria-Geral** responsável pelo sistema de **controle interno** (controle contábil,
  financeiro, orçamentário, operacional e patrimonial).
- **Diretoria de Administração** concentrando o back-office: Patrimônio, Recursos Humanos
  (inclusive **folha de pagamento**), Instituto Histórico, Protocolo/Expediente/Arquivo,
  Almoxarifado, Processamento de Dados e Suporte de Informática, Manutenção e Serviços
  Gerais, Sala de Leitura.
- **Compras** divididas entre a Coordenadoria de Avaliação e Acompanhamento de Compras
  (pesquisa de preços/cotações) e a Coordenadoria de Licitação (atos da Lei 8.666/1993 e da
  **Lei 14.133/2021**).

A comparação 2023 → 2025 evidencia a reforma: criação de Procuradoria-Geral, Ouvidoria-Geral,
Escola do Legislativo, Superintendências e a expansão das coordenadorias — o sistema deve
prever **versões da estrutura organizacional ao longo do tempo**.

---

## 3. Regime de pessoal (módulo de RH)

- Regime jurídico: **Lei Municipal nº 1.506, de 14/01/2000** (Estatuto dos Servidores de
  Duque de Caxias), aplicável aos servidores da Câmara *"no que couber"*, ressalvada a
  competência da Mesa (parágrafo único; [texto no IPMDC](http://ipmdc.com.br/pdf/1506.pdf)).
- Regime **estatutário único** para Executivo e Legislativo; contratados por prazo determinado
  limitados a 2 anos (art. 232).
- Cargos públicos criados **por lei**, com denominação e vencimento próprios, providos em
  caráter **efetivo (concurso)** ou **em comissão** (art. — §2º).
- **Jornada de 30h semanais** em turnos ininterruptos de 6h; ocupantes de cargo em comissão em
  regime de dedicação integral (art. 22).
- **Estágio probatório de 36 meses**, avaliado por assiduidade, disciplina, responsabilidade,
  iniciativa, produtividade e eficácia (art. 23); remoção por permuta entre Poderes por ato
  do chefe respectivo.
- Quadro efetivo conhecido (concurso de 2012, [Edital 001/2012](https://cdn.direcaoconcursos.com.br/uploads/2021/02/edital-Concurso-p%C3%BAblico-Duque-de-Caxias-RJ-C%C3%A2mara.pdf),
  autorizado pela Resolução nº 2.379/2011 — 57 vagas): Adjunto de Plenário e Portaria,
  Auxiliar Legislativo, Técnico de Documentação Parlamentar, Técnico em Administração
  Legislativa, Agente de Processamento de Dados, Assistente Financeiro, Inspetor de Segurança
  do Legislativo, Consultor Contábil, Consultor Jurídico, Inspetor Jurídico, Redator,
  Supervisor Legislativo, Técnico de Comunicação Social e Técnico Legislativo.

---

## 4. O que o sistema precisa cobrir (mapa setores → módulos)

| Módulo do sistema | Setores atendidos (Lei 3.525/2025) | Regras-chave |
|---|---|---|
| **Processo legislativo** (proposições, tramitação, sessões, votações, atas) | Diretoria de Plenário; Coord. de Apoio Legislativo, Assuntos de Plenário, Atas e Projetos, Redação Oficial | Regimento Interno; integração com painel de plenário |
| **Protocolo e documentos** | Coordenadoria da Secretaria-Geral; Documentação Histórica | Numeração única, arquivo, digitalização |
| **RH / folha** | Coordenadoria de Recursos Humanos; Departamento do e-Social | Lei 1.506/2000 (30h, estágio probatório 36m); GAL até 150%, adicionais 40–60%; eSocial |
| **Compras e licitações** | Coord. de Avaliação e Acompanhamento de Compras; Licitações e Contratos; Material; Patrimônio | Lei 14.133/2021; agentes de contratação com gratificação de 40% |
| **Orçamento, finanças e contabilidade** | Coordenadorias de Contabilidade e Finanças | Empenho/liquidação/pagamento; prestação de contas ao TCE-RJ |
| **Controle interno** | Controladoria-Geral | Controle contábil, financeiro, orçamentário, operacional e patrimonial |
| **Jurídico** | Procuradoria-Geral; Consultoria-Geral Legislativa | Pareceres, representação judicial (adicional de 40% do Consultor Jurídico) |
| **Transparência e comunicação** | Coord. de Publicações e Transparência; Cerimonial e Comunicação Social; Ouvidoria-Geral | LAI, publicidade da produção legislativa, portal da transparência |
| **Gabinetes** | Assessorias parlamentares (3º grau), Assistência às Comissões | Lotação por gabinete, indicação pelos titulares |
| **Segurança e serviços** | Polícia Legislativa; Prevenção a Incêndio; serviços auxiliares (4º grau) | Escalas, patrimônio, manutenção predial |
| **TI** | Coordenadoria de Tecnologia da Informação e Comunicação | Infraestrutura do próprio sistema |

**Referência funcional existente:** o [SAPL (Interlegis/Senado Federal)](https://www12.senado.leg.br/interlegis/produtos/sapl),
gratuito e open-source, já cobre elaboração e tramitação de proposições, sessões plenárias,
base de leis e consultas de Mesa/comissões/votações, com acompanhamento cidadão — serve de
baseline para o módulo legislativo (avaliar integrar ou substituir).

---

## 5. Lacunas a resolver antes da modelagem final

1. **Anexos I–III da Lei 3.525/2025** (quantitativos, símbolos e remuneração dos comissionados
   e funções gratificadas) não estão na publicação online — obter cópia integral na CMDC.
2. **Regimento Interno** e **Lei Orgânica**: as versões consolidadas não puderam ser
   verificadas nas fontes confiáveis desta rodada (as páginas do leismunicipais.com.br não
   passaram na verificação); confirmar no site oficial os fluxos regimentais de tramitação.
3. Subordinação exata de cada coordenadoria de 2º grau (a lei indica subordinação à
   Diretoria-Geral, mas o detalhamento por órgão superior precisa ser conferido no texto
   integral com anexos).
4. Plano de cargos e carreiras posterior a 2012 (se houver lei específica atualizando o
   quadro efetivo).

---

## 6. Fontes primárias confirmadas

1. [Lei nº 3.525/2025 — site oficial CMDC](https://www.cmdc.rj.gov.br/?p=30397)
2. [Organograma CMDC 30/10/2023 (PDF oficial)](https://www.cmdc.rj.gov.br/wp-content/uploads/2023/10/organograma_30_10_2023_14_40.pdf)
3. [Lei Municipal 1.506/2000 — Estatuto dos Servidores (IPMDC)](http://ipmdc.com.br/pdf/1506.pdf)
4. [Edital 001/2012 do concurso da CMDC](https://cdn.direcaoconcursos.com.br/uploads/2021/02/edital-Concurso-p%C3%BAblico-Duque-de-Caxias-RJ-C%C3%A2mara.pdf)
5. [SAPL — Interlegis/Senado Federal](https://www12.senado.leg.br/interlegis/produtos/sapl)
