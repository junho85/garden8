import configparser
import os
from datetime import date, timedelta, datetime
import yaml


class ConfigTools:
    def __init__(self):
        self.config_dir = self.init_config_dir()
        self.config = self.load_config()
        self.users = self.load_users()

    def init_config_dir(self):
        """
        GARDEN_CONFIG_DIR 환경변수 값이 있으면 GARDEN_CONFIG_DIR 를 사용하고
        없으면 ./config/attendance 를 기본값으로 사용합니다.

        로컬 개발 환경에서는 ./config/attendance 에 파일을 만들어서 사용하고
        배포 환경에서는 GARDEN_CONFIG_DIR 설정을 상황에 맞춰 사용하면 되겠음

        :return:
        """
        env_config_dir = os.environ.get('GARDEN_CONFIG_DIR')
        if env_config_dir:
            return env_config_dir

        config_dir = "./config/attendance"
        return config_dir


    def make_db_tools(self):
        """
        config.ini 의 [DATABASE] 로 DBTools 를 만든다.
        MongoTools 를 대체하는 자리이고, 호출부는 이 메서드만 쓰면 된다.
        """
        from attendance.db_tools import DBTools
        pg = self.config['DATABASE']
        return DBTools(
            host=pg['HOST'],
            port=pg['PORT'],
            database=pg['DATABASE'],
            user=pg['USER'],
            password=pg['PASSWORD'],
            schema=pg['SCHEMA'],
        )

    def load_config(self):
        config = configparser.ConfigParser()
        path = os.path.join(self.config_dir, 'config.ini')
        config.read(path)
        return config

    def get_config(self):
        return self.config

    def get_gardening_days(self):
        return self.config['DEFAULT']['GARDENING_DAYS']

    def get_start_date_str(self):
        return self.config['DEFAULT']['START_DATE']

    def get_start_date(self):
        return datetime.strptime(self.get_start_date_str(),
                          "%Y-%m-%d").date()  # start_date e.g.) 2021-01-18

    def load_users(self):
        """
        load users.yaml
        :return: users_with_slackname
        """
        path = os.path.join(self.config_dir, 'users.yaml')
        with open(path) as file:
            users_with_slackname = yaml.full_load(file)

        return users_with_slackname

    def get_users(self):
        return self.users

    def get_user_slacknames(self):
        return [self.users[user]["slack"] for user in self.users]

    def get_slack_api_token(self):
        return self.config['DEFAULT']['SLACK_API_TOKEN']

    def get_commit_channel_id(self):
        return self.config['DEFAULT']['CHANNEL_ID']

    def get_monitor_channel_id(self):
        return self.config['MONITOR']['CHANNEL_ID']

