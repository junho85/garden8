from attendance.config_tools import ConfigTools


class AttendanceRepository:
    def __init__(self):
        self.config_tools = ConfigTools()

        self.db_tools = self.config_tools.make_db_tools()

    def get_messages_by_author_name(self, author_name):
        return self.db_tools.find_by_author_name(author_name)