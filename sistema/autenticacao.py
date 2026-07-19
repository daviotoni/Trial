"""Autenticação e autorização por unidade (setor).

Senhas com PBKDF2-SHA256 (biblioteca padrão) e sessões por token
aleatório. O acesso é controlado por **unidade**: o usuário é lotado num
setor real da Lei 3.525/2025 e herda as áreas que aquele setor opera
(`unidade_area`). Um `perfil` legado serve de compatibilidade quando não
há lotação; o ADMIN (Diretoria-Geral/TI) é superusuário.

Duas travas dão sentido a "cada setor faz só o que lhe cabe":
- `exigir`: a unidade do usuário tem alçada sobre a área da operação;
- `exigir_posse`: o processo está na unidade do usuário (só quem detém o
  processo o encaminha ao setor seguinte).

Demonstração: python -m sistema.autenticacao
"""

from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3

# Áreas funcionais do sistema (usadas na marcação das rotas da API).
AREAS = {"PESSOAL", "FOLHA", "PROTOCOLO", "LEGISLATIVO", "COMPRAS",
         "TRANSPARENCIA", "CONTROLE", "JURIDICO", "COMUNICACAO", "SEGURANCA",
         "SERVICOS", "PATRIMONIO", "DOCUMENTACAO", "OUVIDORIA", "CAPACITACAO",
         "PLANEJAMENTO", "ADMINISTRACAO", "USUARIOS"}

# O que cada perfil pode operar.
PERFIS = {
    "ADMIN": AREAS,
    "RH": {"PESSOAL", "FOLHA"},
    "PROTOCOLO": {"PROTOCOLO"},
    "LEGISLATIVO": {"LEGISLATIVO"},
    "COMPRAS": {"COMPRAS"},
    "CONTROLE": {"CONTROLE", "TRANSPARENCIA", "FOLHA"},
}

# Senha inicial do admin. Em produção, defina ADMIN_SENHA_INICIAL no
# ambiente; sem ela, usa o padrão documentado (troque no primeiro acesso).
SENHA_INICIAL_ADMIN = os.environ.get("ADMIN_SENHA_INICIAL", "cmdc@2026")


class AcessoNegado(Exception):
    """Usuário autenticado, mas sem alçada para a operação."""


class NaoAutenticado(Exception):
    """Operação exige login."""


def _hash_senha(senha: str, sal: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", senha.encode(), sal, 100_000).hex()


def criar_usuario(banco: sqlite3.Connection, login: str, senha: str,
                  perfil: str, servidor_id: int | None = None,
                  unidade_id: int | None = None) -> int:
    """Cria um usuário.

    `unidade_id` é a lotação (setor). Quando informada, o acesso passa a
    vir das áreas mapeadas para a unidade (`unidade_area`); sem ela, o
    `perfil` funciona como alçada (compatibilidade). ADMIN é superusuário.
    """
    if perfil not in PERFIS:
        raise ValueError(f"perfil deve ser um de: {', '.join(sorted(PERFIS))}")
    if len(senha) < 8:
        raise ValueError("senha deve ter ao menos 8 caracteres")
    sal = secrets.token_bytes(16)
    return banco.execute(
        "INSERT INTO usuario (login, senha_hash, sal, perfil, servidor_id, "
        "unidade_id) VALUES (?, ?, ?, ?, ?, ?)",
        (login, _hash_senha(senha, sal), sal.hex(), perfil, servidor_id,
         unidade_id),
    ).lastrowid


def autenticar(banco: sqlite3.Connection, login: str, senha: str) -> dict | None:
    """Confere as credenciais; devolve {login, perfil, unidade_id} ou None."""
    linha = banco.execute(
        "SELECT senha_hash, sal, perfil, unidade_id FROM usuario "
        "WHERE login = ? AND ativo = 1", (login,),
    ).fetchone()
    if linha is None:
        return None
    senha_hash, sal, perfil, unidade_id = linha
    if not secrets.compare_digest(senha_hash,
                                  _hash_senha(senha, bytes.fromhex(sal))):
        return None
    return {"login": login, "perfil": perfil, "unidade_id": unidade_id}


def garantir_admin_inicial(banco: sqlite3.Connection) -> bool:
    """Cria o usuário 'admin' (senha inicial documentada) se não houver
    nenhum usuário cadastrado. Devolve True se criou."""
    (total,) = banco.execute("SELECT COUNT(*) FROM usuario").fetchone()
    if total:
        return False
    criar_usuario(banco, "admin", SENHA_INICIAL_ADMIN, "ADMIN")
    return True


class Sessoes:
    """Tokens de sessão em memória (token → {login, perfil})."""

    def __init__(self):
        self._ativas: dict[str, dict] = {}

    def abrir(self, usuario: dict) -> str:
        token = secrets.token_hex(24)
        self._ativas[token] = usuario
        return token

    def usuario(self, token: str | None) -> dict | None:
        if not token:
            return None
        return self._ativas.get(token)

    def encerrar(self, token: str) -> None:
        self._ativas.pop(token, None)


def areas_do_usuario(banco: sqlite3.Connection, usuario: dict) -> set[str]:
    """Áreas que o usuário pode operar.

    - ADMIN: todas (superusuário);
    - lotado numa unidade: as áreas mapeadas para essa unidade;
    - sem unidade: o mapa do perfil (compatibilidade).
    """
    if usuario["perfil"] == "ADMIN":
        return set(AREAS)
    if usuario.get("unidade_id"):
        return {
            area for (area,) in banco.execute(
                "SELECT area FROM unidade_area WHERE unidade_id = ?",
                (usuario["unidade_id"],),
            )
        }
    return set(PERFIS.get(usuario["perfil"], set()))


def exigir(banco: sqlite3.Connection, usuario: dict | None, area: str) -> dict:
    """Valida que há usuário logado com alçada na área. Devolve o usuário."""
    if usuario is None:
        raise NaoAutenticado("operação exige login (envie o token no "
                             "cabeçalho Authorization: Bearer <token>)")
    if area not in areas_do_usuario(banco, usuario):
        onde = (f"a unidade do usuário {usuario['login']}"
                if usuario.get("unidade_id") else f"o perfil {usuario['perfil']}")
        raise AcessoNegado(f"{onde} não tem alçada sobre {area}")
    return usuario


def _unidade_atual_do_processo(banco: sqlite3.Connection,
                               processo_id: int) -> int | None:
    """Unidade onde o processo está: último destino de tramitação ou origem."""
    linha = banco.execute(
        """SELECT COALESCE(
             (SELECT unidade_destino_id FROM tramitacao
               WHERE processo_id = ? ORDER BY id DESC LIMIT 1),
             (SELECT unidade_origem_id FROM processo WHERE id = ?))""",
        (processo_id, processo_id),
    ).fetchone()
    return linha[0] if linha else None


def exigir_posse(banco: sqlite3.Connection, usuario: dict,
                 processo_id: int) -> None:
    """Garante que o setor do usuário é o que detém o processo agora.

    É o "cada setor só age no processo que está com ele". ADMIN e usuários
    sem lotação (perfil legado) não são limitados por posse.
    """
    if usuario["perfil"] == "ADMIN" or not usuario.get("unidade_id"):
        return
    atual = _unidade_atual_do_processo(banco, processo_id)
    if atual is not None and usuario["unidade_id"] != atual:
        raise AcessoNegado(
            "o processo não está na sua unidade; só o setor que o detém "
            "pode encaminhá-lo")


def acoes_da_unidade(banco: sqlite3.Connection, usuario: dict) -> set[str]:
    """Ações específicas que a unidade do usuário pode praticar."""
    if usuario["perfil"] == "ADMIN":
        return {"*"}
    if not usuario.get("unidade_id"):
        return set()
    return {
        acao for (acao,) in banco.execute(
            "SELECT acao FROM unidade_acao WHERE unidade_id = ?",
            (usuario["unidade_id"],),
        )
    }


def exigir_acao(banco: sqlite3.Connection, usuario: dict, acao: str) -> None:
    """Trava fina por competência: a unidade do usuário pode praticar a ação?

    ADMIN e usuários sem lotação (perfil legado) não são limitados por
    ação — a área já os autorizou. Um setor lotado precisa ter a ação
    explicitamente atribuída (unidade_acao).
    """
    if usuario["perfil"] == "ADMIN" or not usuario.get("unidade_id"):
        return
    permitidas = acoes_da_unidade(banco, usuario)
    if acao not in permitidas:
        raise AcessoNegado(
            f"o setor {usuario['login']} não tem competência para {acao} "
            "(a lei atribui esse ato a outro órgão)")


def main() -> None:
    from sistema import servicos
    from sistema.demo import criar_banco

    banco = criar_banco()

    def uid(nome):
        return banco.execute(
            "SELECT id FROM unidade WHERE nome = ?", (nome,)).fetchone()[0]

    print("=" * 66)
    print("ACESSO POR UNIDADE — cada setor só o que lhe cabe")
    print("=" * 66)

    setores = [
        ("gab.chiquinho", "LEGISLATIVO",
         "Gabinete do(a) Vereador(a) Chiquinho Caipira"),
        ("prot.maria", "PROTOCOLO", "Coordenadoria da Secretaria-Geral"),
        ("cpl.jose", "COMPRAS", "Comissão Permanente de Licitação"),
        ("rh.ana", "RH", "Coordenadoria de Recursos Humanos"),
    ]
    for login, perfil, unidade in setores:
        criar_usuario(banco, login, "senha123", perfil, unidade_id=uid(unidade))
        u = autenticar(banco, login, "senha123")
        areas = ", ".join(sorted(areas_do_usuario(banco, u)))
        print(f"\n{login:<14} → {unidade}")
        print(f"  áreas: {areas}")

    print("\n" + "=" * 66)
    print("POSSE DO PROCESSO — só quem o detém encaminha")
    print("=" * 66)
    gab_a = autenticar(banco, "gab.chiquinho", "senha123")
    prot = autenticar(banco, "prot.maria", "senha123")
    origem = uid("Gabinete do(a) Vereador(a) Chiquinho Caipira")
    pid, numero = servicos.autuar_processo(
        banco, "LEGISLATIVO", "PL de exemplo", origem, "2025-09-10")
    print(f"\nProcesso {numero} autuado no gabinete (origem).")
    print(f"  gabinete detém → pode encaminhar? "
          f"{_pode(banco, gab_a, pid)}")
    print(f"  protocolo (não detém) → pode encaminhar? "
          f"{_pode(banco, prot, pid)}")
    banco.close()


def _pode(banco, usuario, processo_id) -> str:
    try:
        exigir_posse(banco, usuario, processo_id)
        return "SIM"
    except AcessoNegado:
        return "NÃO"


if __name__ == "__main__":
    main()
