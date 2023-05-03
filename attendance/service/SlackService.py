from datetime import datetime

from attendance.config_tools import ConfigTools
from attendance.mongo_tools import MongoTools
from attendance.slack_tools import SlackTools


class SlackService:
    def __init__(self):
        self.config_tools = ConfigTools()

        self.slack_tools = SlackTools(
            slack_api_token=self.config_tools.get_slack_api_token(),
            commit_channel_id=self.config_tools.get_commit_channel_id(),
        )

        self.slack_client = self.slack_tools.get_slack_client()
        self.slack_commit_channel_id = self.slack_tools.get_commit_channel_id()

        self.users_with_slackname = self.config_tools.get_users()

        self.mongo_tools = MongoTools(
            host=self.config_tools.config['MONGO']['HOST'],
            port=self.config_tools.config['MONGO']['PORT'],
            database=self.config_tools.config['MONGO']['DATABASE'],
            username=self.config_tools.config['MONGO']['USERNAME'],
            password=self.config_tools.config['MONGO']['PASSWORD']
        )

    def remove_all_slack_messages(self):
        """
        db 에 수집한 slack 메시지 삭제
        """
        mongo_collection = self.mongo_tools.get_collection()
        mongo_collection.remove()

    def send_no_show_message(self, attendances, channel='#gardening-for-100days'):
        """
        미출석자 알람
        :param attendances:
        :return:
        """
        members = self.get_users_with_slackname()

        message = "[미출석자 알람]\n"
        for attendance in attendances:
            if attendance["first_ts"] is None:
                message += "@%s " % members[attendance["user"]]["slack"]

        self.slack_client.chat_postMessage(
            channel=channel,
            text=message,
            link_names=1
        )

    def get_users_with_slackname(self):
        """
        github userid - slack username
        """
        return self.users_with_slackname

    def send_error_message(self, message):
        self.slack_client.chat_postMessage(
            channel=self.config_tools.get_monitor_channel_id(),
            text=message
        )
