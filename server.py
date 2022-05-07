##############################################################################
# server.py
##############################################################################

import socket
import chatlib
import select
from collections import OrderedDict
from operator import getitem
import random
import firebase_admin
from firebase_admin import credentials, firestore
import requests
import html
import hashlib
import time

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {"databaseURL": "https://python-trivia-mor-default-rtdb.firebaseio.com/"})
# save data
db = firestore.client()
users_collection = db.collection('users')
# GLOBALS
users = {}
questions = {}
logged_users = {}  # a dictionary of client hostnames to usernames - will be used later
client_sockets = []
ERROR_MSG = "Error! "
SERVER_PORT = 5678
SERVER_IP = "0.0.0.0"
MAX_MSG_LENGTH = 1204
messages_to_send = []


def get_questions():
    """
     get from api the trivia questions
    :return:  a list of 50 questions
    """
    global questions
    response = requests.get("https://opentdb.com/api.php?amount=50&type=multiple")
    return response.json()


# HELPER SOCKET METHODS
def print_client_sockets(sockets: list):
    for c in sockets:
        print("\t", c.getpeername())


def build_and_send_message(conn: socket.socket, code, msg):
    """
      Builds a new message using chatlib, wanted code and message.
      Prints debug info, then sends it to the given socket.
      Paramaters: conn (socket object), code (str), data (str)
      Returns: Nothing
      """
    global messages_to_send
    full_msg = chatlib.build_message(code, msg)
    messages_to_send.append((conn, full_msg))

    print("[SERVER] ", full_msg)  # Debug print


def recv_message_and_parse(conn):
    """
        Recieves a new message from given socket,
        then parses the message using chatlib.
        Paramaters: conn (socket object)
        Returns: cmd (str) and data (str) of the received message.
        If error occured, will return None, None
        """
    full_msg = conn.recv(1024).decode()
    cmd, data = chatlib.parse_message(full_msg)
    print("[CLIENT] ", full_msg)  # Debug print
    return cmd, data


# SOCKET CREATOR

def setup_socket():
    """
    Creates new listening socket and returns it
    Recieves: -
    Returns: the socket object
    """
    # Implement code ...
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((SERVER_IP, SERVER_PORT))
    sock.listen()
    return sock


def send_error(conn, error_msg):
    """
    Send error message with given message
    Recieves: socket, message error string from called function
    Returns: None
    """
    build_and_send_message(conn, chatlib.PROTOCOL_SERVER["error_msg"], error_msg)


##### MESSAGE HANDLING

def handle_logout_message(conn: socket.socket):
    """
    Closes the given socket (in laster chapters, also remove user from logged_users dictioary)
    Recieves: socket
    Returns: None
    """
    global logged_users
    client_sockets.remove(conn)
    if conn in logged_users:
        del logged_users[conn]
    conn.close()
    print("logout")
    print_client_sockets(client_sockets)


def handle_login_message(conn: socket.socket, data: str):
    """
    Gets socket and message data of login message. Checks  user and pass exists and match.
    If not - sends error and finished. If all ok, sends OK message and adds user and address to logged_users
    Recieves: socket, message code and data
    Returns: None (sends answer to client)
    TODO: prevent login from user that is already connected
    """
    try:
        global users  # This is needed to access the same users dictionary from all functions
        global logged_users  # To be used later
        global users_collection
        user_data = chatlib.split_data(data, 1)
        if not user_data[0] in logged_users.values():
            user = users_collection.where("username", "==", user_data[0]).get()[0]
            if user:
                if user.get("password") == user_data[1]:
                    build_and_send_message(conn, chatlib.PROTOCOL_SERVER["login_ok_msg"], "")
                    logged_users[conn] = user.id
                else:
                    send_error(conn, "wrong password")
            else:
                send_error(conn, "user not found")
        else:
            send_error(conn, "user already logged in")
    except Exception as err:
        print(err)


def handle_sign_up_message(conn: socket.socket, data: str):
    """
    The function saves data of user sent by a sign up request
    :param conn: socket representing the client's connection
    :param data: data sent by the user. should include a username and password
    """
    try:
        global users  # This is needed to access the same users dictionary from all functions
        global logged_users  # To be used later
        global users_collection
        user_data = chatlib.split_data(data, 1)
        if users_collection.where("username", "==", user_data[0]).get():
            send_error(conn, "Username is taken")
        else:
            doc_ref = users_collection.document()
            doc_ref.set({
                "username": user_data[0],
                "password": user_data[1],
                "score": 0,
                "questions_asked": []
            })
            build_and_send_message(conn, chatlib.PROTOCOL_SERVER["signup_ok_msg"], "")
    except Exception as err:
        print(err)


def handle_client_message(conn: socket.socket, cmd: str, data: str):
    """
    Gets message code and data and calls the right function to handle command
    Recieves: socket, message code and data
    Returns: None
    """
    global logged_users  # To be used later
    if conn not in logged_users:
        if cmd == chatlib.PROTOCOL_CLIENT["login_msg"]:
            handle_login_message(conn, data)
        elif cmd == chatlib.PROTOCOL_CLIENT["signup_msg"]:
            handle_sign_up_message(conn, data)
        else:
            send_error(conn, "invalid command")
    else:
        if cmd == chatlib.PROTOCOL_CLIENT["logout_msg"]:
            handle_logout_message(conn)
        elif cmd == chatlib.PROTOCOL_CLIENT["highscore"]:
            handle_highscore_message(conn)
        elif cmd == chatlib.PROTOCOL_CLIENT["user_score"]:
            handle_getscore_message(conn)
        elif cmd == chatlib.PROTOCOL_CLIENT["logged_users"]:
            handle_logged_message(conn)
        elif cmd == chatlib.PROTOCOL_CLIENT["question"]:
            handle_question_message(conn)
        elif cmd == chatlib.PROTOCOL_CLIENT["send_answer"]:
            handle_answer_message(conn, data)
        else:
            send_error(conn, "invalid command")


def handle_getscore_message(conn):
    """
    Sending to the user it's current score
    :param conn: A socket instance of the connection with the user
    """
    user = users_collection.document(logged_users[conn]).get()
    score = user.get("score")
    build_and_send_message(conn, chatlib.PROTOCOL_SERVER["user_score"], str(score))


def handle_highscore_message(conn):
    """
    Getting a lead users table, showing top 50.
    :param conn: A socket instance of the connection with the user
    """
    sorted_highs = users_collection.order_by("score", direction="DESCENDING").order_by("score_timestamp").get()
    user_rank = sorted_highs.index(users_collection.document(logged_users[conn]).get())
    top_list = sorted_highs[0:50]
    score_msg = "You current rank: " + str(user_rank) + "\n\n"
    rank_num = 1
    for user in top_list:
        score_msg += str(rank_num) + ". " + user.get("username") + ": " + str(user.get("score")) + "\n"
        rank_num += 1
    build_and_send_message(conn, chatlib.PROTOCOL_SERVER["highscore"], score_msg)


def handle_logged_message(conn):
    """
    Sending a list of all connected users
    :param conn: A socket instance of the connection with the user
    """
    global logged_users
    global users_collection
    user_names = []
    for user_id in logged_users.values():
        user_names.append(users_collection.document(user_id).get().get("username"))
    logged_users_list = ",".join(user_names)
    build_and_send_message(conn, chatlib.PROTOCOL_SERVER["logged_users"], logged_users_list)


def create_random_question():
    """
    Randomly selecting a question of the questions list
    :return: a list containing question id, questions and answers
    """
    global questions
    selected_question = random.choice(questions)
    selected_question_id = str(hash(selected_question["question"]))
    answers_list = selected_question["incorrect_answers"] + [selected_question["correct_answer"]]
    random.shuffle(answers_list)
    return chatlib.join_data(
        [selected_question_id, selected_question["question"]] + answers_list)


def handle_question_message(conn: socket.socket):
    """
    Sending to user a random question with choices. the question id is saves in the user's record in order to no be
    repeated.
    :param conn: A socket instance of the connection with the user
    """
    global users_collection
    user = users_collection.document(logged_users[conn])
    questions_asked = user.get().get("questions_asked")
    if len(questions_asked) == 500:
        build_and_send_message(conn, chatlib.PROTOCOL_SERVER["finished_game"], "")
    while True:
        question = create_random_question()
        if not question.split("#")[0] in questions_asked:
            break
    build_and_send_message(conn, chatlib.PROTOCOL_SERVER["question"], question)
    user.update({"questions_asked": questions_asked + [question.split("#")[0]]})


def handle_answer_message(conn: socket.socket, answer_msg):
    """
    checking the answer selected by the user. If correct, 5 points are added to score.
    :param conn:
    :param answer_msg:
    """
    answer_data = chatlib.split_data(answer_msg, 1)
    if not len(answer_data) == 2:
        send_error(conn, "Error reading answer data")
    question_id = int(answer_data[0])
    answer_id = answer_data[1]
    if len(answer_id) != 64:
        send_error(conn, "Invalid answer identifier")
    correct_answer = ""
    for q in questions:
        if hash(q["question"]) == question_id:
            correct_answer = q["correct_answer"]
            break
    if hashlib.sha256(correct_answer.encode()).hexdigest() == answer_id:
        user = users_collection.document(logged_users[conn])
        score = user.get().get("score")
        user.update({"score": score + 5})
        build_and_send_message(conn, chatlib.PROTOCOL_SERVER["correct_answer"], "")
    else:
        build_and_send_message(conn, chatlib.PROTOCOL_SERVER["wrong_answer"], str(correct_answer))


def main():
    # Initializes global users and questions dicionaries using load functions, will be used later
    global users
    global questions
    global messages_to_send
    questions = get_questions()["results"]
    for question in questions:
        question["question"] = html.unescape(question["question"])
        question["correct_answer"] = html.unescape(question["correct_answer"])
        for i in range(len(question["incorrect_answers"])):
            question["incorrect_answers"][i] = html.unescape(question["incorrect_answers"][i])
    print("Welcome to Trivia Server!")
    server_socket = setup_socket()
    while True:
        ready_to_read, ready_to_write, in_error = select.select([server_socket] + client_sockets, client_sockets, [])
        for curr_socket in ready_to_read:
            if curr_socket is server_socket:
                client_socket, client_address = server_socket.accept()
                print("new client joined")
                client_sockets.append(client_socket)
                print_client_sockets(client_sockets)
            else:
                print("new data from client")
                try:
                    cmd, data = recv_message_and_parse(curr_socket)
                    if cmd is None:
                        raise Exception("invalid message")
                    handle_client_message(curr_socket, cmd, data)
                except Exception as err:
                    handle_logout_message(curr_socket)
            for message in messages_to_send:
                current_socket, data = message
                if current_socket in ready_to_write:
                    current_socket.send(data.encode())
                    messages_to_send.remove(message)


if __name__ == '__main__':
    main()
