from litestar import Controller, get


class AccountController(Controller):
    path = "/accounts"

    @get("/", sync_to_thread=False)
    def list_accounts(self) -> dict[str, str]:
        return {"status": "ok"}
