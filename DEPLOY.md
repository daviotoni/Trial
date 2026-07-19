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

## Dados que persistem de verdade

Para o banco sobreviver a reinícios e atualizações, escolha uma opção:

1. **Disco no Render (mais simples)** — em um plano pago do serviço,
   adicione um **Disk** montado em `/data` e defina a variável
   **`CMDC_DB=/data/cmdc.db`**. O SQLite passa a viver no disco e persiste.
2. **Banco PostgreSQL** — o `schema.sql` já é portável para PostgreSQL; é a
   opção robusta para produção com muitos usuários (requer adaptar a camada
   de acesso ao banco).

## Outras plataformas

O projeto também traz um **`Procfile`** (`web: python -m sistema.api`), então
funciona em plataformas como Railway ou Heroku pelo mesmo comando. O
servidor lê `PORT`, `HOST` e `CMDC_DB` do ambiente.

## Rodar no seu próprio computador (opcional)

Com Python 3.11+ instalado, dentro da pasta do projeto:

```bash
python -m sistema.api        # abre em http://127.0.0.1:8000
```
