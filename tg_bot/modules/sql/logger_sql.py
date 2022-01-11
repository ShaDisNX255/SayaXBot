import threading

from sqlalchemy import Column, String, Boolean

from tg_bot.modules.sql import BASE, SESSION




class LoggerSettings(BASE):
    __tablename__ = "chat_log_settings"
    chat_id = Column(String(14), primary_key=True)
    setting = Column(Boolean, default=False, nullable=False)

    def __init__(self, chat_id, disabled):
        self.chat_id = str(chat_id)
        self.setting = disabled

    def __repr__(self):
        return "<Chat log setting {} ({})>".format(self.chat_id, self.setting)


LoggerSettings.__table__.create(checkfirst=True)

LOG_SETTING_LOCK = threading.RLock()


def enable_chat_log(chat_id):
    with LOG_SETTING_LOCK:
        chat = SESSION.query(LoggerSettings).get(str(chat_id))
        if not chat:
            chat = LoggerSettings(chat_id, True)

        chat.setting = True
        SESSION.add(chat)
        SESSION.commit()


def disable_chat_log(chat_id):
    with LOG_SETTING_LOCK:
        chat = SESSION.query(LoggerSettings).get(str(chat_id))
        if not chat:
            chat = LoggerSettings(chat_id, False)

        chat.setting = False
        SESSION.add(chat)
        SESSION.commit()


def does_chat_log(chat_id):
    with LOG_SETTING_LOCK:
        d = SESSION.query(LoggerSettings).get(str(chat_id))
        if not d:
            return False
        return d.setting



def __load_chat_log_stat_list():
    global LOGSTAT_LIST
    try:
        LOGSTAT_LIST = {
            x.chat_id for x in SESSION.query(LoggerSettings).all() if x.setting
        }
    finally:
        SESSION.close()


def migrate_chat(old_chat_id, new_chat_id):
    with LOG_SETTING_LOCK:
        chat = SESSION.query(LoggerSettings).get(str(old_chat_id))
        if chat:
            chat.chat_id = new_chat_id
            SESSION.add(chat)

        SESSION.commit()


# Create in memory userid to avoid disk access
__load_chat_log_stat_list()


def migrate_chat(old_chat_id, new_chat_id):
    with LOG_SETTING_LOCK:
        chat_notes = (
            SESSION.query(LoggerSettings)
            .filter(LoggerSettings.chat_id == str(old_chat_id))
            .all()
        )
        for note in chat_notes:
            note.chat_id = str(new_chat_id)
        SESSION.commit()
