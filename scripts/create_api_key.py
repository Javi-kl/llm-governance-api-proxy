from app.db.database import get_db_context
from app.services.api_keys import create_for_user
from app.core import exceptions


def main() -> None:
    username = input("Username: ")
    key_name = input("Nombre de la API key: ")

    try:
        with get_db_context() as db:
            raw_key = create_for_user(
                username=username,
                key_name=key_name,
                db=db,
            )

            print(f"API key: {raw_key}")

    except exceptions.UserNotFoundError as exc:
        print(exc.message)
    except ValueError:
        print("Nombre de la api key no valido.")


if __name__ == "__main__":
    main()
