import socket
import chatlib  # To use chatlib functions or consts, use chatlib.****
import hashlib

SERVER_IP = "127.0.0.1"  # Our server will run on same computer as client
SERVER_PORT = 5678


# HELPER SOCKET METHODS

def build_and_send_message(conn: socket.socket, code: str, data: str):
    """
    Builds a new message using chatlib, wanted code and message.
    Prints debug info, then sends it to the given socket.
    Paramaters: conn (socket object), code (str), data (str)
    Returns: Nothing
    """
    full_msg = chatlib.build_message(code, data)
    conn.send(full_msg.encode())


def recv_message_and_parse(conn: socket.socket):
    """
    Recieves a new message from given socket,
    then parses the message using chatlib.
    Paramaters: conn (socket object)
    Returns: cmd (str) and data (str) of the received message.
    If error occured, will return None, None
    """
    full_msg = conn.recv(1024).decode()
    cmd, data = chatlib.parse_message(full_msg)
    return cmd, data


def build_send_recv_parse(conn: socket.socket, code: str, data: str):
    """
     Sending through socket message to server and return its response
    :param conn: A connection socket of the client with the server.
    :param code: A string which indicates of what function the server should use
    :param data: relevant data to bo joined with the request. May be an empty string
    :return: Returned a parsed response of the server containing code and data
    """
    build_and_send_message(conn, code, data)
    return recv_message_and_parse(conn)


def get_score(conn: socket.socket):
    """
    Requesting the user's score
    :param conn: A connection socket of the client with the server.
    """
    code, score = build_send_recv_parse(conn, "MY_SCORE", "")
    if code == "YOUR_SCORE":
        print("Your score is: " + score)
    else:
        error_and_exit(code)


def get_highscore(conn: socket.socket):
    """
    :param conn: A connection socket of the client with the server.
    """
    code, score = build_send_recv_parse(conn, "HIGHSCORE", "")
    if code == "ALL_SCORE":
        print("Highscore:\n" + score)
    else:
        error_and_exit(code)


def play_question(conn):
    """
    Requesting a random questions from the server and play it to the user
    :param conn: A connection socket of the client with the server.
    """
    question_id = -1
    while question_id == -1:
        code, question = build_send_recv_parse(conn, chatlib.PROTOCOL_CLIENT["question"], "")
        if code == chatlib.PROTOCOL_SERVER["question"]:
            question = question.split("#")
            question_id = question[0]
    print(question[1] + "\n")
    for i in range(2, len(question)):
        print(str(i - 1) + ". " + question[i])
        has_answered = False
    while not has_answered:
        answer = input("Select your answer")
        if answer.isdigit():
            answer = answer
        else:
            print("please enter a valid answer number")
            continue
        if 1 <= int(answer) <= 4:
            code, correct_answer = build_send_recv_parse(conn, chatlib.PROTOCOL_CLIENT["send_answer"],
                                                         question[0] + "#" + hashlib.sha256(
                                                             question[int(answer) + 1].encode()).hexdigest())
            if code == chatlib.PROTOCOL_SERVER["finished_game"]:
                print("Well done, you've answered the maximum amount of questions")
            if code == chatlib.PROTOCOL_SERVER["wrong_answer"]:
                print("wrong answer, correct answer is: " + correct_answer)
            elif code == chatlib.PROTOCOL_SERVER["correct_answer"]:
                print("that's correct")
            else:
                error_and_exit("Error occurred :" + code)
                return
            has_answered = True
        else:
            print("please enter a valid answer number")
            continue


def connect():
    """
    Establishing a connection with the server
    :return: A socket of the established connection between the client and server.
    """
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((SERVER_IP, SERVER_PORT))
    return client_socket


def error_and_exit(error_msg):
    """
    Triggered when an error occurred. An error message is printed and the client's execution stops.
    :param error_msg: Message with information about the error.
    """
    print(error_msg)
    exit()


def auth_user(conn: socket.socket):
    """
    Allowing the user to authenticate to the software by signing in or signing up.
    :param conn:  A connection socket of the client with the server.
    """
    action = input("Please enter your choice:\n"
                   "l               Login\n"
                   "s               Sign Up\n"
                   "q               Quit\n")
    if action == "l":
        login(conn)
    elif action == "s":
        signup(conn)
    else:
        exit()


def login(conn):
    """
    Signing in a user to the game
    :param conn:   A connection socket of the client with the server.
    """
    cmd = ""
    while cmd != chatlib.PROTOCOL_SERVER["login_ok_msg"]:
        username = input("Please enter username: \n")
        password = input("Please enter password: \n")
        build_and_send_message(conn, chatlib.PROTOCOL_CLIENT["login_msg"], username + "#" + password)
        cmd, data = recv_message_and_parse(conn)
        print(data)
    print("Login success")


def logout(conn):
    """
    Logging out user from the game. The Afterwards connection with the server is closed
    :param conn:  A connection socket of the client with the server.
    """
    build_and_send_message(conn, chatlib.PROTOCOL_CLIENT["logout_msg"], "")
    print("logout")


def signup(conn: socket.socket):
    """
    Signing up a user to the game
    :param conn:   A connection socket of the client with the server.
    :param conn: A connection socket of the client with the server.
    """
    cmd = ""
    while cmd != chatlib.PROTOCOL_SERVER["signup_ok_msg"]:
        is_valid = False
        while not is_valid:
            username = input("enter username\n")
            if username.isalnum():
                is_valid = True
            else:
                print("User can contain only letters and digits")
            if not len(username) >= 4:
                is_valid = False
                print("User must contains at least 4 characters")
        is_valid = False
        while not is_valid:
            password = input("enter password\n")
            if len(password) >= 5:
                is_valid = True
            else:
                print("Password must contains at least 5 characters")
            if not password.isalnum():
                is_valid = False
                print("Password can contain only letters and digits")
        cmd, data = build_send_recv_parse(conn, chatlib.PROTOCOL_CLIENT["signup_msg"], username + "#" + password)
        print(data)


def get_logged_users(conn: socket.socket):
    """
    Requesting a list of all the connected users. The list is printed
    :param conn:  A connection socket of the client with the server.
    """
    code, users = build_send_recv_parse(conn, chatlib.PROTOCOL_CLIENT["logged_users"], "")
    if code == chatlib.PROTOCOL_SERVER["logged_users"]:
        print(users)
    else:
        error_and_exit("error getting logged in users")


def main():
    try:
        conn = connect()
        auth_user(conn)
        while True:
            action = input("Please enter your choice:\n"
                           "s               Get my score\n"
                           "h               Get high score\n"
                           "p               Play a trivia question\n"
                           "l               Get logged users\n"
                           "q               Quit\n")

            if action == "s":
                get_score(conn)
            elif action == "p":
                play_question(conn)
            elif action == "h":
                get_highscore(conn)
            elif action == "l":
                get_logged_users(conn)
            elif action == "q":
                break
            else:
                print("Invalid choice please press one of the keys above")
        logout(conn)
        conn.close()
    except Exception as ex:
        print("Error occurred")
        exit()

if __name__ == '__main__':
    main()
