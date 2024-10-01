from flask import Flask, request, abort

from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    PushMessageRequest
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)

import os
from argparse import ArgumentParser
from chatgpt import reply_conversation_with_context, reply_conversation_with_session_id
from event_keeper import log_event
import time
import random
from datetime import datetime

app = Flask(__name__)

configuration = Configuration(access_token=os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

sent_messages = {
    "morning": False,
    "night": False
}

@app.route("/webhook", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        # log event
        log_event(event.to_dict())

        # save user id
        os.environ["user_id"] = event.source.user_id

        # mimic chatgpt
        reply = reply_conversation_with_session_id(event.message.text, event.source.user_id)

        # delay
        delay_time = random.uniform(3, 10)
        time.sleep(delay_time)

        log_event({"datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "type": "reply", "to_user_id": event.source.user_id,"response": reply})
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(text=reply),  
                ]
            )
        )

def send_push_message(user_id, message_text):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        try:
            push_message_request = PushMessageRequest(
                to=user_id,
                messages=[TextMessage(text=message_text)]
            )
            line_bot_api.push_message(
                push_message_request
            )
            print(f"Push message sent to {user_id}: {message_text}")
        except Exception as e:
            print(f"Error sending push message: {e}")

def find_user_id_and_send_messages_every_five_seconds():
    while True:
        if "user_id" in os.environ:
            send_push_message(os.environ["user_id"], "This is a message sent every 5 seconds.")
            time.sleep(5)  # Wait for 5 seconds before sending the next message

def send_messages_based_on_time(user_id):
    morning_messages = ["good morining", "morning!", "Are you awake?"]
    night_messages = ["good night", "night", "talk to you tomorrow, good night"]
    while True:
        current_time = datetime.now()
        # Morning time check (7 AM to 10 AM)
        if 7 <= current_time.hour < 10 and not sent_messages["morning"]:
            message = random.choice(morning_messages)
            send_push_message(user_id, message)
            log_event({"datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "type": "push", "to_user_id": user_id,"response": message})
            sent_messages["morning"] = True  # Mark as sent

        # Night time check (10 PM to 11 PM)
        elif 22 <= current_time.hour < 23 and not sent_messages["night"]:
            message = random.choice(night_messages)
            send_push_message(user_id, message)
            log_event({"datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "type": "push", "to_user_id": user_id,"response": message})
            sent_messages["night"] = True  # Mark as sent

        # Reset sent messages at the end of each period
        if current_time.hour >= 10 and current_time.hour < 22:
            sent_messages["morning"] = False  # Reset for the next morning period
        if current_time.hour >= 23:  # After 11 PM, reset night message
            sent_messages["night"] = False

        # Wait between 30 mins to 2 hours to check again
        delay_time = random.uniform(1800, 7200)
        time.sleep(delay_time)


if __name__ == "__main__":
    arg_parser = ArgumentParser(
        usage='Usage: python ' + __file__ + ' [--port <port>] [--help]'
    )
    arg_parser.add_argument('-p', '--port', default=3000, help='port')
    arg_parser.add_argument('-d', '--debug', default=False, help='debug')
    options = arg_parser.parse_args()

    # Start sending messages in a separate thread
    import threading
    message_thread = threading.Thread(target=send_messages_based_on_time)
    message_thread.daemon = True  # This allows the thread to exit when the main program does
    message_thread.start()

    app.run(debug=options.debug, port=options.port)