"""Autenticação e autorização por perfil de setor.

Senhas com PBKDF2-SHA256 (biblioteca padrão) e sessões por token
aleatório. Os perfis espelham os setores da Lei 3.525/2025; cada perfil
enxerga apenas as áreas do sistema que lhe competem — o ADMIN
(Diretoria-Geral/TI) enxerga todas.
"""

from __future__ import annotations

import hashlib
import secrets
import sqlite3

# Áreas funcionais do sistema (usadas na marcação das rotas da API).
AREAS = {"PESSOAL", "FOLHA", "PROTOCOLO", "LEGISLATIVO", "COMPRAS",
         "TRANSPARENCIA", "CONTROLE", "USUARIOS"}

# O que cada perfil pode operar.
PERFIS = {
    "ADMIN": AREAS,
    "RH": {"PESSOAL", "FOLHA"},
    "PROTOCOLO": {"PROTOCOLO"},
    "LEGISLATIVO": {"LEGISLATIVO"},
    "COMPRAS": {"COMPRAS"},
    "CONTROLE": {"CONTROLE", "TRANSPARENCIA", "FOLHA"},
}

SENHA_INICIAL_ADMIN = "cmdc@2026"  # trocar no primeiro acesso


class AcessoNegado(Exception):
    """Usuário autenticado, mas sem alçada para a operação."""


class NaoAutenticado(Exception):
    """Operação exige login."""


def _hash_senha(senha: str, sal: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", senha.encode(), sal, 100_000).hex()


def criar_usuario(banco: sqlite3.Connection, login: str, senha: str,
                  perfil: str, servidor_id: int | None = None) -> int:
    if perfil not in PERFIS:
        raise ValueError(f"perfil deve ser um de: {', '.join(sorted(PERFIS))}")
    if len(senha) < 8:
        raise ValueError("senha deve ter ao menos 8 caracteres")
    sal = secrets.token_bytes(16)
    return banco.execute(
        "INSERT INTO usuario (login, senha_hash, sal, perfil, servidor_id) "
        "VALUES (?, ?, ?, ?, ?)",
        (login, _hash_senha(senha, sal), sal.hex(), perfil, servidor_id),
    ).lastrowid


def autenticar(banco: sqlite3.Connection, login: str, senha: str) -> dict | None:
    """Confere as credenciais; devolve {login, perfil} ou None."""
    linha = banco.execute(
        "SELECT senha_hash, sal, perfil FROM usuario "
        "WHERE login = ? AND ativo = 1", (login,),
    ).fetchone()
    if linha is None:
        return None
    senha_hash, sal, perfil = linha
    if not secrets.compare_digest(senha_hash,
                                  _hash_senha(senha, bytes.fromhex(sal))):
        return None
    return {"login": login, "perfil": perfil}


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


def exigir(usuario: dict | None, area: str) -> dict:
    """Valida que há usuário logado com alçada na área. Devolve o usuário."""
    if usuario is None:
        raise NaoAutenticado("operação exige login (envie o token no "
                             "cabeçalho Authorization: Bearer <token>)")
    if area not in PERFIS.get(usuario["perfil"], set()):
        raise AcessoNegado(
            f"perfil {usuario['perfil']} não tem alçada sobre {area}"
        )
    return usuario
