from datetime import datetime

from garden import Garden

from attendance.config_tools import ConfigTools

import pprint
import requests

from urllib.parse import urlparse

config_tools = ConfigTools()


garden = Garden()

db_tools = config_tools.make_db_tools()


def get_commit(commit_url):
    parse_result = urlparse(commit_url)
    # print(parse_result)
    (_, user, repo, commit, sha) = parse_result.path.split("/")

    api_url = 'https://api.github.com/repos/%s/%s/commits/%s' % (user, repo, sha)

    r = requests.get(api_url)

    # pprint(r)
    # print(r.json())
    commit_json = r.json()

    ts_datetime = datetime.strptime(commit_json["commit"]["author"]["date"], "%Y-%m-%dT%H:%M:%S%z")
    commit_message = commit_json["commit"]["message"]
    ts = str(ts_datetime.timestamp())
    return {
        "user": user,
        "ts": ts,
        "ts_datetime": ts_datetime,
        "sha": sha,
        "sha_short": sha[:8],
        "message": commit_message,
    }


def manual_insert(commit_url):
    commit = get_commit(commit_url)
    print("commit:")
    print(commit)
    print("user:" + commit["user"])
    print("sha:" + commit["sha"])
    print("sha_short:" + commit["sha_short"])
    print("ts:" + commit["ts"])
    print("ts_datetime:" + str(commit["ts_datetime"]))
    print("ts_datetime %Y-%m-%d:" + commit["ts_datetime"].strftime("%Y-%m-%d"))
    print("message:" + commit["message"])

    today = datetime.today().strftime("%Y-%m-%d")
    fallback = '*manual insert %s by june.kim* - commit by %s' % (today, commit["user"])
    text = '`<%s|%s>` - %s' % (commit_url, commit["sha_short"], commit["message"])

    user = 'U02LXDBJZRV'
    message = {'attachments':
        [{
            'fallback': fallback,
            'text': text
        }],
        'author_name': commit["user"],
        'ts': commit["ts"],
        'ts_for_db': commit["ts_datetime"],
        'type': 'message',
        'user': user
    }

    pprint.pprint(message)
    # exit(-1)

    try:
        result = db_tools.upsert_message(message)
        pprint.pprint(result)
        print(message)
    except Exception as e:
        print(e)


commit_urls = [
    # 오스카
    # 'https://github.com/lunaticfoxy/TIL/commit/295f8bfa02a1d65794eacb95dec3ca05d08bd7bb', # 11.15
]

for commit_url in commit_urls:
    manual_insert(commit_url)
