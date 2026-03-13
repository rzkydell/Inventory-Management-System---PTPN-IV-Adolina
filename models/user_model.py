from database.connection import get_connection


def login_user(username, password):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (username, password)
    )

    user = cursor.fetchone()

    conn.close()

    return user


def register_user(username, password):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            "INSERT INTO users (username,password) VALUES (?,?)",
            (username, password)
        )

        conn.commit()

        return True

    except Exception as e:

        print("REGISTER ERROR:", e)

        return False

    finally:

        conn.close()