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
  hierarquia técnico-administrativa** (art. 2º, parágrafo único). Os Gabinetes dos membros da
  Mesa e dos Vereadores são considerados unidades administrativas (art. 1º, parágrafo único).
- A **Diretoria-Geral** é o *órgão central de apoio administrativo*, **diretamente subordinada
  à Presidência** (art. 15).
- Cargos comissionados são providos por **Portaria do Presidente** (art. 3º); os lotados em
  gabinetes, por indicação dos titulares (§2º), podendo atuar em regime externo, escalas
  diferenciadas, fins de semana/noturno e trabalho remoto (§3º).
- Servidor efetivo nomeado para cargo em comissão recebe **gratificação de 100% do valor do
  cargo** enquanto durar o exercício (art. 3º, §4º).
- A Mesa Diretora pode transformar, extinguir ou remanejar cargos comissionados e funções
  gratificadas por Resolução, sem aumento de despesa (art. 3º, §5º).
- Funções de confiança gratificadas exigem ato do Presidente, qualificação compatível e
  **mínimo de 2 anos de efetivo exercício** na Câmara (art. 5º, §3º); guardam equivalência
  remuneratória com os cargos em comissão de símbolo correspondente (§4º).
- **Vigência**: publicada em 29/08/2025, com efeitos financeiros a partir de **01/09/2025**
  (art. 102). **Extingue** todos os cargos comissionados das Leis 2.653/2014 e 3.233/2022 e
  os que não constem da nova lei (art. 99); revoga o Anexo Único e art. 3º da Lei 2.653/2014
  e dispositivos da Lei 3.233/2022 (art. 101).

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
A gratificação de comissão (arts. 46–47) é **indenizatória, precária e não incorporável**, paga
só durante atuação efetiva, com base de incidência à escolha do servidor efetivo que também
ocupe cargo comissionado (art. 46, §3º) — regra de folha não trivial que o sistema deve suportar.

### 1.3 Anexo I — quadro de cargos comissionados e funções gratificadas (615 vagas)

O Anexo I ("Cargos Isolados de Provimento em Comissão e Funções de Confiança Gratificadas")
traz 49 denominações somando **615 vagas**: **602 cargos em comissão** e **13 funções de
confiança** (símbolos FC-1/FC-2, que por nota do próprio anexo existem apenas como função
gratificada, sem cargo em comissão correspondente — ou seja, exercidas por servidores efetivos).

Faixas de retribuição-base: R$ 15.925 (DAS-8/FC-1 — direção superior), R$ 12.250 (SAS-6),
R$ 10.125 (SL-1), R$ 6.870 (CAE-1, FC-2, GAB-1, PAR-2/3, ASS diversos), R$ 4.125, R$ 3.000
e R$ 1.560.

Destaques quantitativos (espelham os 29 gabinetes parlamentares):

| Cargo | Símbolo | Vagas | Retribuição (R$) |
|---|---|---|---|
| Assessor Parlamentar I | PAR-3 | 96 | 6.870 |
| Assessor Parlamentar II | PAR-2 | 96 | 6.870 |
| Assistente de Gabinete I | ASS-10 | 90 | 3.000 |
| Assessor Parlamentar III | PAR-1 | 70 | 6.870 |
| Assistente de Gabinete II | ASS-11 | 70 | 1.560 |
| Assistente das Comissões Permanentes | ASS-5 | 33 | 4.125 |
| Assessor de Comissão Legislativa e Parlamentar | ASS-1 | 31 | 6.870 |
| Secretário Legislativo | SL-1 | 29 | 10.125 |
| Chefe de Gabinete | GAB-1 | 29 | 6.870 |
| Assessor de Plenário | ASS-6 | 29 | 4.125 |

Dirigentes de unidade: 8 cargos DAS-8 de R$ 15.925 (Diretor-Geral, Procurador-Geral,
Consultor-Geral Legislativo, Diretor de Plenário, Diretor da Escola do Legislativo,
Superintendente-Geral, Assessor de Assuntos Especiais, Consultor Especial das Comissões
Técnicas), Controlador-Geral como **função de confiança FC-1** (controle interno exercido por
efetivo), Superintendente de Assuntos Estratégicos (SAS-6), Ouvidor-Geral e Diretor
Administrativo (CAE-1) e os 20 coordenadores (FC-2 ou CAE-1).

> A tabela completa do Anexo I está codificada em `orgao/cmdc.py` (`ANEXO_I`).

### 1.4 Comissões permanentes de apoio à administração (art. 45)

Cinco comissões permanentes, com membros preferencialmente efetivos e gratificação de 40%:
**Licitação**, **Recebimento Definitivo de Obras, Serviços e Bens**, **Aplicação de Sanções**
(arts. 156–160 da Lei 14.133/2021), **Proteção de Dados Pessoais** (adequação à LGPD, em
articulação com a ANPD) e **Atualização e Consolidação de Leis e Normas Municipais**.
Comissões temporárias: até 180 dias, prorrogáveis por 90 (art. 47). O **Departamento do
e-Social** (4º grau, art. 48) integra RH, Contabilidade e Controle Interno para as obrigações
do eSocial — integração obrigatória do módulo de folha.

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

## 5. Regimento Interno — Resolução nº 1.835, de 13/07/2000

Localizado no [site oficial (PDF, 105 p.)](https://www.cmdc.rj.gov.br/wp-content/uploads/2013/06/Regimento_Interno_da_Camara.pdf)
e arquivado em `docs/regimento-interno-res-1835-2000.pdf` (texto extraído no `.txt`
correspondente). Alterado ao longo do tempo por resoluções (ex.: 1.946/2002 — voto aberto;
2.399/2013 — comissões; 2.725/2019 — licenças, art. 252; 2.910/2025 — art. 101, §1º).

Regras regimentais relevantes para o sistema:

- **Comissões permanentes (art. 33)**: 20 comissões temáticas (Legislação, Justiça e
  Redação Final; Finanças e Orçamento; Educação e Cultura; Saúde e Assistência Social;
  Transportes; Defesa do Consumidor; Obras e Serviços Públicos; Meio Ambiente; Fiscalização;
  Desenvolvimento Urbano; Direitos da Mulher e da Criança e Adolescente; Direitos Humanos;
  Portadores de Necessidades Especiais; Segurança Alimentar; Segurança; Esporte, Lazer e
  Turismo; Prevenção e Combate às Drogas; Combate à Pirataria; Direitos dos Idosos;
  Direitos da Juventude) — distintas das comissões administrativas do art. 45 da Lei
  3.525/2025.
- **Sessões ordinárias** com início às 17h30 e partes definidas (art. 75); abertura exige
  **maioria absoluta** para a ordem do dia; regras detalhadas de quórum e adiamento.
- **Votação ostensiva** — simbólica (regra geral) ou nominal, sempre com **voto aberto**
  (art. 180, redação da Res. 1.946/2002); verificação de votação a pedido.
- **Maioria absoluta** para Projeto de Lei Complementar (art. 178) e outras hipóteses
  qualificadas (deliberações de comissões exigem presença da maioria absoluta, art. — Seção
  das Comissões).

## 6. Resolução da GAL — **não existe até junho/2026**

O art. 7º, parágrafo único, da Lei 3.525/2025 remete os critérios de fixação do percentual
da GAL a Resolução da Mesa Diretora. Varredura completa das resoluções publicadas no site
oficial entre a nº 2.910 (11/02/2025) e a nº 2.938 (30/06/2026): **nenhuma regulamenta a
GAL** — a quase totalidade trata de títulos honoríficos. Achados correlatos para o módulo
de RH: [Resolução 2.929/2026](https://www.cmdc.rj.gov.br/?p=31478) (controle de
frequência/ponto dos servidores) e [Resolução 2.938/2026](https://www.cmdc.rj.gov.br/?p=32300)
(consignações em folha). A [Lei 3.558/2025](https://www.cmdc.rj.gov.br/?p=31180) altera a
Lei 1.506/2000 (bonificação natalina de R$ 250 em 2025, não incorporável), sem tocar a
3.525.

**Implicação prática**: desde 01/09/2025 a GAL tem teto legal (150%) mas não tem critérios
regulamentados — no sistema, o percentual é parâmetro obrigatório do cálculo, validado
contra o teto, ficando pronto para receber os critérios quando a Resolução for editada.

## 7. Lacunas remanescentes

1. ~~Anexos da Lei 3.525/2025~~ — **resolvido** (Anexo I codificado em `orgao/cmdc.py`).
2. ~~Regimento Interno~~ — **resolvido** (Res. 1.835/2000 arquivada em `docs/`); confirmar
   com a Secretaria se há consolidação mais recente que o PDF publicado.
3. ~~Resolução da GAL~~ — **verificado: inexistente até jun/2026** (acompanhar edição).
4. Plano de cargos e carreiras **efetivos** posterior a 2012.
5. Lei nº 3.226/2022 (benefícios do art. 17, referida no art. 4º da Lei 3.525/2025).
6. Lei Orgânica consolidada ([PDF oficial](https://www.cmdc.rj.gov.br/wp-content/uploads/2013/06/Lei_Organica_Municipal.pdf)
   disponível; incorporar se necessário).

---

## 8. Fontes primárias confirmadas

1. [Lei nº 3.525/2025 — site oficial CMDC](https://www.cmdc.rj.gov.br/?p=30397)
2. [Organograma CMDC 30/10/2023 (PDF oficial)](https://www.cmdc.rj.gov.br/wp-content/uploads/2023/10/organograma_30_10_2023_14_40.pdf)
3. [Lei Municipal 1.506/2000 — Estatuto dos Servidores (IPMDC)](http://ipmdc.com.br/pdf/1506.pdf)
4. [Edital 001/2012 do concurso da CMDC](https://cdn.direcaoconcursos.com.br/uploads/2021/02/edital-Concurso-p%C3%BAblico-Duque-de-Caxias-RJ-C%C3%A2mara.pdf)
5. [SAPL — Interlegis/Senado Federal](https://www12.senado.leg.br/interlegis/produtos/sapl)
6. [Regimento Interno — Res. 1.835/2000 (PDF oficial)](https://www.cmdc.rj.gov.br/wp-content/uploads/2013/06/Regimento_Interno_da_Camara.pdf)
7. [Categoria Resoluções do site da CMDC](https://www.cmdc.rj.gov.br/?cat=9) (varredura 2.910–2.938)
