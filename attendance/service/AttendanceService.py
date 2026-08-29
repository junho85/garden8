import logging

from attendance.config_tools import ConfigTools
from attendance.repository.AttendanceRepository import AttendanceRepository
from datetime import date, timedelta, datetime


class AttendanceService:
    def __init__(self):
        # logger 세팅
        # level = logging.DEBUG
        level = logging.INFO
        logging.basicConfig(level=level,
                            format='%(asctime)s [%(process)d] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s')

        self.attendance_repository = AttendanceRepository()

        self.config_tools = ConfigTools()

        self.users_with_slackname = self.config_tools.get_users()
        self.users = list(self.users_with_slackname.keys())

        self.start_date = self.config_tools.get_start_date()

        self.db_tools = self.config_tools.make_db_tools()

    def get_commits_with_ts_by_user(self, user):
        results = []
        for message in self.attendance_repository.get_messages_by_author_name(author_name=user):
            for attachment in message["attachments"]:
                try:
                    """
                    커밋 내역만 추출합니다

                    * 커밋 내역은 text 필드를 가집니다.
                    * 단, Pull request opened도 text 필드를 가지고 있습니다.
                      * 이 경우 pretext 필드가 있고 "Pull request opened by"로 시작하기 때문에 해당 내역을 제외합니다.
                    """
                    # commit has text field
                    # there is no text field in pull request, etc...

                    # filter Pull request opened by
                    if "pretext" in attachment and attachment["pretext"].startswith("Pull request opened by"):
                        continue

                    for commit_text in attachment["text"].split("\n"):
                        results.append({
                            "ts": message["ts"],
                            "ts_for_db": message["ts_for_db"],
                            "commit_text": commit_text
                        })
                    # logging.info(f'text={attachment["text"]}')
                    # logging.info(markdown.markdown(attachment["text"], extensions=[PythonMarkdownSlack()]))

                    # if "Guide to Spring Bean Scopes" in attachment["text"]:
                    #     logging.info("****************")
                    #     logging.info(message)
                except Exception as err:
                    # logging.info(attachment)
                    # logging.info(message["attachments"])
                    # logging.info(err)
                    continue
        return results

    def find_attendances_by_user(self, user):
        """
        # 특정 유저의 전체 출석부를 생성함
        # TODO 출석부를 DB에 넣고 마지막 생성된 출석부 이후의 데이터로 추가 출석부 만들도록 하자
        :param user:
        :return:
        """
        result = {}

        start_date = self.start_date

        for commit in self.get_commits_with_ts_by_user(user=user):
            # make attend
            ts_datetime = commit["ts_for_db"]
            attend = {
                "ts": ts_datetime,
                "message": commit["commit_text"]
            }

            # current date and date before day1
            date = ts_datetime.date()
            date_before_day1 = date - timedelta(days=1)
            hour = ts_datetime.hour

            if date_before_day1 >= start_date and hour < 3 and date_before_day1 not in result:
                # check before day1. if exists, before day1 is already done.
                result[date_before_day1] = []
                result[date_before_day1].append(attend)
            else:
                # create date commits array
                if date not in result:
                    result[date] = []

                result[date].append(attend)

        return result

    def get_attendances(self, users, date):
        """
        특정일의 출석 데이터 불러오기
        :param users: list of users
        :param date
        :return: list of attendances
        """
        attend_dict = {}

        # get all users attendance info
        for user in users:
            attends = self.find_attendances_by_user(user)
            attend_dict[user] = attends

        result = {}
        result_attendance = []

        # make users - dates - first_ts
        for user in attend_dict:
            if user not in result:
                result[user] = {}

            result[user][date] = None

            if date in attend_dict[user]:
                result[user][date] = attend_dict[user][date][0]["ts"]

            result_attendance.append({"user": user, "first_ts": result[user][date]})

        return result_attendance
