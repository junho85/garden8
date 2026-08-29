from datetime import date, timedelta, datetime

import pprint

from attendance.service.SlackService import SlackService
from attendance.slack_tools import SlackTools
from attendance.config_tools import ConfigTools


class Garden:
    def __init__(self):
        self.config_tools = ConfigTools()
        self.slack_tools = SlackTools(
            slack_api_token=self.config_tools.get_slack_api_token(),
            commit_channel_id=self.config_tools.get_commit_channel_id(),
        )
        self.db_tools = self.config_tools.make_db_tools()

        self.slack_client = self.slack_tools.get_slack_client()
        self.slack_commit_channel_id = self.slack_tools.get_commit_channel_id()

        self.slack_service = SlackService()

        self.gardening_days = self.config_tools.get_gardening_days()
        self.start_date = self.config_tools.get_start_date()
        self.start_date_str = self.config_tools.get_start_date_str()

        self.users_with_slackname = self.config_tools.get_users()
        self.users = list(self.users_with_slackname.keys())

    def get_gardening_days(self):
        return self.gardening_days

    def get_start_date(self):
        return self.start_date

    def get_start_date_str(self):
        return self.start_date_str

    def get_users(self):
        return self.users

    def find_attend(self, oldest, latest):
        print("find_attend")
        print(oldest)
        print(datetime.fromtimestamp(oldest))
        print(latest)
        print(datetime.fromtimestamp(latest))

        for message in self.db_tools.find_by_ts_for_db_range(
                datetime.fromtimestamp(oldest), datetime.fromtimestamp(latest)):
            print(message["ts"])
            print(message)

    def collect_slack_messages(self, oldest, latest):
        """
        github 봇으로 모은 slack message 들을 slack_messages collection 에 저장
        :param oldest:
        :param latest:
        :return:
        """
        response = self.slack_client.conversations_history(
            channel=self.slack_commit_channel_id,
            latest=str(latest),
            oldest=str(oldest),
            limit=1000  # default 100
        )

        messages = response["messages"]
        for message in messages:
            if "attachments" not in message:
                continue

            # pprint.pprint(message)
            message["ts_for_db"] = datetime.fromtimestamp(float(message["ts"]))
            try:
                message["author_name"] = self.slack_tools.get_author_name_from_commit_message(
                    message["attachments"][0]["fallback"])
            except Exception as err:
                print(message["attachments"])
                print(err)
                continue
            # print(message["author_name"])

            # ts 가 unique 라 중복은 upsert 로 흡수된다(기존 DuplicateKeyError 자리).
            self.db_tools.upsert_message(message)

        return {
            "start": datetime.fromtimestamp(oldest),
            "end": datetime.fromtimestamp(latest),
            "count": len(messages),
        }
