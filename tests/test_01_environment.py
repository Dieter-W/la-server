"""Environment tests"""

from app.config import TestingConfig


def test_environment_variables(client):

    print("\n")
    print("Environment Variables")
    print("---------------------")
    print("MARIADB_HOST:", TestingConfig.MARIADB_HOST)
    print("MARIADB_DATABASE:", TestingConfig.MARIADB_DATABASE)


# TODO: This should also work for testing the .env variables
# def test_config_is_test(app, client, db_session):
#    assert app.config("TESTING") is True
