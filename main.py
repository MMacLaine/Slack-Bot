# Required modules
import os
import re
import json
from flask import Flask, Response
from slackeventsapi import SlackEventAdapter
from threading import Thread
from slack import WebClient
from slack.errors import SlackApiError
from datetime import datetime

# This `app` represents your existing Flask app
app = Flask(__name__)

slack_token = os.environ['SLACK_BOT_TOKEN']
SLACK_SIGNING_SECRET = os.environ['SLACK_BOT_SIGNING_SECRET']
VERIFICATION_TOKEN = os.environ['SLACK_BOT_VERIFICATION_TOKEN']

# instantiating slack client
slack_client = WebClient(slack_token)


@app.route("/api/slack-bot")
def root():
    return 'Welcome to Slack-Bot'


# Flask health check
@app.route("/api/slack-bot/_health")
def health():
    return {"status": 200}


@app.route("/api/slack-bot/events")
def event_hook(request):
    json_dict = json.loads(request.body.decode("utf-8"))
    if json_dict["token"] != VERIFICATION_TOKEN:
        return {"status": 403}

    if "type" in json_dict:
        if json_dict["type"] == "url_verification":
            response_dict = {"challenge": json_dict["challenge"]}
            return response_dict
    return {"status": 500}


slack_events_adapter = SlackEventAdapter(
    SLACK_SIGNING_SECRET, "/api/slack-bot/events", app
)


@slack_events_adapter.on("app_mention")
def handle_message(event_data):
    def send_reply(value):
        message = value["event"]

        if message.get("subtype") is None:
            command = message.get("text")
            channel_id = message["channel"]

            # check if user is member of required slack channel, edit to channel as needed
            if message["user"] in get_conversation_members(
                    ["C01T006CUAU"]):

                # commands currently added into the bot, will check for command sent via slack          
                if any(item in command.lower() for item in ["help"]):
                    help_message(channel_id, message["user"])

                elif any(item in command.lower() for item in ["empty"]):
                    text = archive_empty_channels()
                    slack_client.chat_postMessage(channel=channel_id, text=text)

                elif any(item in command.lower() for item in ["history"]):
                    text = check_channels_latest_message_history()
                    slack_client.chat_postMessage(channel=channel_id, text=text)

                elif any(item in command.lower() for item in ["warning"]):
                    text = send_channel_owner_warning()
                    slack_client.chat_postMessage(channel=channel_id, text=text)

                elif any(item in command.lower() for item in ["members"]):
                    text = check_number_of_members()
                    slack_client.chat_postMessage(channel=channel_id, text=text)

                elif any(item in command.lower() for item in ["hello", "hello there", "hey", "hej"]):
                    text = (
                            "Hello <@%s>! :tada:"
                            % message["user"]
                    )
                    slack_client.chat_postMessage(channel=channel_id, text=text)

                elif any(item in command.lower() for item in ["guidelines"]):
                    text = check_channels_guidelines()
                    slack_client.chat_postMessage(channel=channel_id, text=text)
                else:
                    help_message(channel_id, message["user"])
            else:
                slack_client.chat_postEphemeral(channel=channel_id, user=message["user"],
                                                text="You are not in the right slack channel")

    thread = Thread(target=send_reply, kwargs={"value": event_data})
    thread.start()
    return Response(status=200)


def help_message(channel_id, user):
    help_text = """
                Welcome to Slack-Bot
                You need to be a member of following slack group: XYZ
                You can use the following commands:
                    - hej: say hello (others might work) :)
                    - Warning: give users a warning before archiving
                    - help: print out this message
                    - empty: get a list of empty channels
                    - members: prints every channel along with their member count
                    - guidelines: get a list of channels according to guidelines
                    - history: get a list of channels with their latest chat message, archive correct channels"""
    slack_client.chat_postEphemeral(channel=channel_id, user=user, text=help_text)


# Check for channels with 0 members. Skipping all channels that are marked as social. Archive all channels found
def archive_empty_channels():
    result = slack_client.conversations_list(limit=1000, types="public_channel")

    channels_to_archive = []

    for channel in result["channels"]:
        if channel["is_channel"] and not channel["is_archived"]:
            channel_id = channel["id"]
            channel_name = channel["name"]

            if channel_name not in ["general"]:
                time_since_message = get_time_since_last_message_in_channel(channel_id)

                if channel["num_members"] <= 50:
                    if time_since_message.days >= 90:
                        channels_to_archive.append((channel_name, channel_id))

                if channel["num_members"] > 50:
                    if time_since_message.days >= 180:
                        channels_to_archive.append((channel_name, channel_id))

    for _, channel_id in channels_to_archive:
        try:
            slack_client.conversations_join(channel=channel_id)
            slack_client.conversations_archive(channel=channel_id)
        except SlackApiError as e:
            print(e.response)

    return "Archiving the following channels \n" + "\n".join(channel[0] for channel in channels_to_archive)


# check if the channel is adhering to the guidelines. (naming convention, having a description)
def check_channels_guidelines():
    result = slack_client.conversations_list(limit=1000)
    channels = [(channel["name"], channel["id"], channel["creator"]) for channel in result["channels"] if
                channel["is_channel"] and "social" not in channel["purpose"]["value"] and not channel["is_archived"]]

    out = ""

    for name, channel_id, creator in channels:
        if re.match("^(all|announcement|se|fr|uk|no|de|global|ask|bet|proj|fdbk|team|fun)-\w+$", name):
            out += f"{name:25s} :white_check_mark:\n"
        else:
            out += f"{name:25s} :x:\n"
            slack_client.conversations_join(limit=1, channel=channel_id)
            # slack_client.chat_postMessage(channel=channel_id, text="To be added")
            # slack_client.chat_postMessage(channel=creator, text="Hi")

    return out


# check if the channel is adhering to the guidelines. (naming convention, having a description)
def check_channels_latest_message_history():
    result = slack_client.conversations_list(limit=1000)
    channels_history = [(channel_history["name"], channel_history["id"]) for channel_history in result["channels"] if
                        channel_history["is_channel"] and not channel_history["is_archived"]]

    header = f"Channel name, Channel user, Days, last message\n"
    out = "Archived \n" + header + "\n"
    out_not_archived = "Not archived \n" + header + "\n"

    for channel_name, channel_id in channels_history:
        slack_client.conversations_join(limit=1, channel=channel_id)
        history = slack_client.conversations_history(limit=1, channel=channel_id)

        last_message = history['messages'][0]
        username = slack_client.users_info(user=last_message['user'])['user']["real_name"]
        time_since_message = datetime.now() - datetime.fromtimestamp(float(last_message['ts']))

        if time_since_message.days >= 365:
            out += f"{channel_name}, {username}, {time_since_message.days} days, {last_message['text']}\n"
            slack_client.conversations_archive(channel=channel_id)
        else:
            out_not_archived += f"{channel_name}, {username}, {time_since_message.days} days, {last_message['text']}\n"

    return out_not_archived + "\n" + out


# Create a list of all channels along with their membership count.
def check_number_of_members():
    result = slack_client.conversations_list(limit=1000, exclude_archived=1, types="public_channel, private_channel")
    all_channel_names_with_numbers = [(channel["name"], channel["num_members"]) for channel in result["channels"] if
                                      channel["is_channel"]]
    return "\n".join("(%s: %s)" % tup for tup in all_channel_names_with_numbers)


def get_time_since_last_message_in_channel(channel_id):
    slack_client.conversations_join(limit=1, channel=channel_id)
    history = slack_client.conversations_history(limit=1, channel=channel_id)

    last_message = history['messages'][0]
    return datetime.now() - datetime.fromtimestamp(float(last_message['ts']))


def get_conversation_members(conversation_ids):
    members = []
    for conversation_id in conversation_ids:
        try:
            members += slack_client.conversations_members(limit=1000, channel=conversation_id).get("members")
        except SlackApiError:
            pass
    return members


# send warning to owner of channel which meet archive needs
def send_channel_owner_warning():
    result = slack_client.conversations_list(limit=1000, types="public_channel")
    warning_text = """
     Hello @channel-owner! We've noticed that this Slack channel (#{})
     has not been actively used for a few months, and has 
     therefore been scheduled to be archived. Once this has been 
     done, all messages will be deleted and the channel will no 
     longer exist after a few more weeks. If this channel is still in use and 
     should not be deleted, anyone can stop the deletion by posting a new
     message in this channel. If no action is taken soon after
     receiving this message, the channel will be archived.
     If you have any questions regarding the bot or the cleanup,
     or have a request to un-archive you can contact us here:
     """
    out = "Following channels: creators have been warned:\n"
    channels = [(channel["name"], channel["id"], channel["creator"], channel["num_members"]) for channel in
                result["channels"] if channel["is_channel"] and not channel["is_archived"]]

    for channel_name, channel_id, channel_creator, channel_num_members in channels:

        if channel_name not in ["general"]:
            time_since_message = get_time_since_last_message_in_channel(channel_id)

            real_name = slack_client.users_profile_get(user=channel_creator)["profile"]["real_name"] or "Unknown"

            if channel_num_members <= 50:
                if time_since_message.days >= 90:
                    out += f"{channel_name}: {real_name}\n"
                    slack_client.chat_postMessage(channel=channel_creator, text=warning_text.format(channel_name))

            if channel_num_members > 50:
                if time_since_message.days >= 180:
                    out += f"{channel_name}: {real_name}\n"
                    slack_client.chat_postMessage(channel=channel_creator, text=warning_text.format(channel_name))

    return out


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8086)
