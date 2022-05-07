# Protocol Constants
CMD_FIELD_LENGTH = 16  # Exact length of cmd field (in bytes)
LENGTH_FIELD_LENGTH = 4  # Exact length of length field (in bytes)
MAX_DATA_LENGTH = 10 ** LENGTH_FIELD_LENGTH - 1  # Max size of data field according to protocol
MSG_HEADER_LENGTH = CMD_FIELD_LENGTH + 1 + LENGTH_FIELD_LENGTH + 1  # Exact size of header (CMD+LENGTH fields)
MAX_MSG_LENGTH = MSG_HEADER_LENGTH + MAX_DATA_LENGTH  # Max size of total message
DELIMITER = "|"  # Delimiter character in protocol
DATA_DELIMITER = "#"  # Delimiter in the data part of the message

# Protocol Messages 
# In this dictionary we will have all the client and server command names

PROTOCOL_CLIENT = {
    "login_msg": "LOGIN",
    "signup_msg": "SIGNUP",
    "logout_msg": "LOGOUT",
    "user_score": "MY_SCORE",
    "highscore": "HIGHSCORE",
    "question": "GET_QUESTION",
    "send_answer": "SEND_ANSWER",
    "logged_users": "LOGGED"
}  # .. Add more commands if needed

PROTOCOL_SERVER = {
    "login_ok_msg": "LOGIN_OK",
    "signup_ok_msg": "SIGN_UP_OK",
    "user_score": "YOUR_SCORE",
    "highscore": "ALL_SCORE",
    "question": "YOUR_QUESTION",
    "correct_answer": "CORRECT_ANSWER",
    "wrong_answer": "WRONG_ANSWER",
    "logged_users": "LOGGED_ANSWER",
    "finished_game": "FINISHED_ANSWER",
    "error_msg": "ERROR"

}  # ..  Add more commands if needed

# Other constants

ERROR_RETURN = None  # What is returned in case of an error


def build_message(cmd, data):
    """
    Gets command name (str) and data field (str) and creates a valid protocol message
    Returns: str, or None if error occured
    """
    if not type(cmd) == str:
        raise ValueError("cmd must be a string")
    if not type(data) == str:
        raise ValueError("data must be a string")
    if cmd not in PROTOCOL_CLIENT.values() and cmd not in PROTOCOL_SERVER.values():
        return None
    if len(data) > MAX_DATA_LENGTH:
        return None
    data_len = str(len(data))
    full_msg = cmd + " " * (16 - len(cmd)) + "|" + "0" * (4 - len(data_len)) + data_len + "|" + data
    return full_msg


def parse_message(data: str):
    """
    Parses protocol message and returns command name and data field
    Returns: cmd (str), data (str). If some error occured, returns None, None
    """
    if not type(data) == str:
        raise ValueError("data must be a string")
    data_split = data.split("|")
    if not len(data_split) == 3:
        return None, None
    cmd = data_split[0].strip()
    field_size = data_split[1].strip()
    if not field_size.isdigit():
        return None, None
    field_size = int(field_size)
    if cmd not in PROTOCOL_CLIENT.values() and cmd not in PROTOCOL_SERVER.values():
        return None, None
    msg = data_split[2]
    if not field_size == len(msg):
        return None, None
    # The function should return 2 values
    return cmd, msg


def split_data(msg, expected_fields):
    if not type(msg) == str:
        raise ValueError("msg must be a string")
    if not type(expected_fields) == int:
        raise ValueError("expected_fields must be an integer")
    """
    Helper method. gets a string and number of expected fields in it. Splits the string
    using protocol's data field delimiter (|#) and validates that there are correct number of fields.
    Returns: list of fields if all ok. If some error occured, returns None
    """
    data_split = msg.split("#")
    if not len(data_split) - 1 == expected_fields:
        return [None]
    return data_split


def join_data(msg_fields):
    """
    Helper method. Gets a list, joins all of it's fields to one string divided by the data delimiter.
    Returns: string that looks like cell1#cell2#cell3
    """
    if not type(msg_fields) == list:
        raise ValueError("msg_fields must be a list")
    return "#".join(msg_fields)
