"""Environment tests"""

# ---------------------------------------------------------------------
# Environment check with print to the console
# ---------------------------------------------------------------------
def test_config_env(app,):  # fmt: skip
    print("\n")
    print("Environment Variables")
    print("---------------------")
    print("MARIADB_HOST:", app.config["MARIADB_HOST"])
    print("MARIADB_DATABASE:", app.config["MARIADB_DATABASE"])
    print("TESTING:", app.config["TESTING"])

    assert app.config["MARIADB_DATABASE"] == "$$test-database$$"
    assert app.config["TESTING"] is True
