"""Configurações da aplicação, lidas de variáveis de ambiente."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _normalize_db_url(url: str) -> str:
    """Garante o driver psycopg3 para URLs de Postgres (Supabase/Heroku usam 'postgres://').

    Também remove espaços e quebras de linha que a colagem no painel de deploy
    costuma introduzir e que truncariam o hostname silenciosamente.
    """
    url = "".join(url.split())
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def describe_db_target(uri: str) -> str:
    """Descreve o destino do banco SEM expor a senha. Para log de diagnóstico."""
    from urllib.parse import urlsplit

    if uri.startswith("sqlite"):
        return "SQLite local"
    p = urlsplit(uri)
    porta = f":{p.port}" if p.port else " (porta padrão)"
    return f"{p.hostname}{porta}{p.path} como {p.username}"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-troque-em-producao")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    _db_url = os.environ.get("DATABASE_URL", "").strip()
    if _db_url:
        SQLALCHEMY_DATABASE_URI = _normalize_db_url(_db_url)
    else:
        # Fallback dev: SQLite local
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{BASE_DIR / 'app.db'}"

    # Segurança de sessão
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("FLASK_ENV") == "production"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = os.environ.get("FLASK_ENV") == "production"
