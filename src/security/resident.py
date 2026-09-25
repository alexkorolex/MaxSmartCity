from litestar.security.jwt import JWTAuth, Token

from src.security.settings import SecuritySettings

RESIDENT_TOKEN_ALGORITHM = "HS256"


def resident_jwt_auth(settings: SecuritySettings) -> JWTAuth:
    """Native litestar[jwt] backend used to mint tokens for residents contacting us via the bot.

    Residents never provide a login/password: the bot authenticates itself with a shared
    secret (see ``src.security.bot``) and this backend then issues a short-lived JWT scoped
    to that one resident, identified by their local ``Resident.id``.
    """
    return JWTAuth(
        token_secret=settings.resident_jwt_secret,
        algorithm=RESIDENT_TOKEN_ALGORITHM,
        retrieve_user_handler=lambda _token, _connection: None,
    )


def decode_resident_token(token: str, settings: SecuritySettings) -> Token:
    """Verify a resident-scoped JWT minted by :func:`resident_jwt_auth`.

    Raises:
        litestar.exceptions.NotAuthorizedException: if the token is missing, expired, or invalid.
    """
    return Token.decode(
        encoded_token=token, secret=settings.resident_jwt_secret, algorithm=RESIDENT_TOKEN_ALGORITHM
    )
