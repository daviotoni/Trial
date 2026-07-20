# Publicar o sistema num servidor (deploy)

Guia para colocar o **Sistema de Gestão da CMDC** no ar num endereço
`https://…`, com **login/senha reais** e vários setores acessando ao mesmo
tempo. O caminho mais simples é o **Render** (plano gratuito, instala
direto do GitHub). Não precisa instalar nada no seu computador.

## Passo a passo (Render — gratuito)

1. Acesse **https://render.com** e clique em **Get Started** — entre com a
   sua conta do **GitHub** (a mesma do repositório `daviotoni/Trial`).
2. No painel, clique em **New +** → **Blueprint**.
3. Conecte o repositório **`daviotoni/Trial`**. Se pedir, autorize o Render
   a acessar o GitHub.
4. Em **Branch**, selecione **`claude/repo-exploration-rw4wex`** (o ramo com
   o sistema). O Render vai ler o arquivo `render.yaml` automaticamente.
5. Clique em **Apply**. O Render cria o serviço `sistema-cmdc` e começa a
   publicar (leva ~2 minutos).
6. Quando terminar, o endereço aparece no topo, algo como
   **`https://sistema-cmdc.onrender.com`**. É o seu link — abre em qualquer
   navegador.

## Primeiro acesso

- Usuário: **`admin`**  ·  Senha: **`cmdc@2026`**
- **Troque a senha** e crie os usuários de cada setor (aba/rota de usuários),
  cada um lotado na sua unidade.

Para definir outra senha inicial do admin, no Render vá em **Environment** e
crie a variável **`ADMIN_SENHA_INICIAL`** com o valor desejado (antes do
primeiro deploy, ou reinicie o serviço depois).

## O que esperar do plano gratuito

- **Multiusuário e público**: vários setores podem logar ao mesmo tempo. ✅
- **Dorme após ~15 min sem uso**: a primeira visita depois disso demora
  ~30 s para "acordar". Normal no plano gratuito.
- **Dados não persistem entre reinícios/atualizações**: o banco (SQLite) é
  recriado a cada reinício. Ótimo para **piloto/demonstração**; para uso
  real, veja abaixo.

## Dados que persistem de verdade (Supabase — gratuito)

O sistema fala PostgreSQL nativamente (adaptador em
`sistema/bancodados.py`). Basta apontar a variável **`DATABASE_URL`** para
um banco Supabase e os dados passam a sobreviver a reinícios e
atualizações. Passo a passo:

1. No painel do Supabase (supabase.com/dashboard), abra o projeto e clique
   em **Connect** (topo). Copie a URI do **Session pooler** (porta 5432) —
   use o *pooler*, não a conexão direta (o Render não alcança a direta,
   que é só IPv6).
2. A URI traz `[YOUR-PASSWORD]`: pegue/defina a senha do banco em
   **Project Settings → Database → Reset database password** e substitua.
3. No Render, no serviço, abra **Environment** → **Add Environment
   Variable**: chave `DATABASE_URL`, valor = a URI completa. Salve — o
   serviço reinicia sozinho.
4. No primeiro arranque o app cria o schema e a carga inicial no Supabase
   (bootstrap idempotente); nas próximas, só reutiliza.

### Conferir se a persistência está ativa: rota `/saude`

Abra **`https://SEU-APP.onrender.com/saude`** no navegador. A resposta diz
qual banco a instância no ar está usando:

- `{"backend": "postgres", "persistente": true, ...}` → **funcionando**: os
  dados estão no Supabase e sobrevivem a reinícios. ✅
- `{"backend": "sqlite", "persistente": false, ...}` → a `DATABASE_URL` **não
  chegou** ao Postgres. Ou a variável não foi salva no Render, ou a URL está
  incorreta e o app caiu no SQLite efêmero (veja os **Logs** do serviço no
  Render — há um aviso explicando o erro).

### Erro comum: conexão direta em vez do *pooler*

O Supabase oferece dois endereços. A **conexão direta**
(`db.<ref>.supabase.co`) é só IPv6 e o Render **não alcança** — use sempre o
**Session pooler** (host `*.pooler.supabase.com`, porta 5432). Se a
`DATABASE_URL` apontar para a direta, ou a senha estiver errada, o app agora
**não cai** — ele sobe em SQLite efêmero e o `/saude` mostra
`backend=sqlite`. Corrija a URL no Render (Environment) e salve; o serviço
reinicia e o `/saude` deve passar a `postgres`.

Notas: no plano gratuito do Supabase o banco hiberna após ~1 semana sem
uso (reativa no painel). As sessões de login vivem em memória — após um
reinício do app é preciso entrar de novo (os dados permanecem).

Alternativas: disco pago no Render (`CMDC_DB=/data/cmdc.db`) ou outro
PostgreSQL qualquer via `DATABASE_URL`.

## Outras plataformas

O projeto também traz um **`Procfile`** (`web: python -m sistema.api`), então
funciona em plataformas como Railway ou Heroku pelo mesmo comando. O
servidor lê `PORT`, `HOST` e `CMDC_DB` do ambiente.

## Rodar no seu próprio computador (opcional)

Com Python 3.11+ instalado, dentro da pasta do projeto:

```bash
python -m sistema.api        # abre em http://127.0.0.1:8000
```
