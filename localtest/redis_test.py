import redis
from redis.commands.json.path import Path
import time


d = {"hello": "world", "key": "value"}
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
r.ping()
then = time.perf_counter()
print(r.json().get("7132bf5d2b39d0d1eec0c5209c5b041750fe445f7399d316477748dc51b094e8"))
# for i in range(100000):
#     with r.pipeline() as pipe:
#         pipe.json().set(f"somekey{i}", Path.rootPath(), d)
#         pipe.expire(f"somekey{i}", 1)
#         pipe.execute()
# time.sleep(2)
# print(r.json().get("somekey"))
now = time.perf_counter() - then
print(now)

# r = rejson.Client(host='localhost', port=6379, db=0, decode_responses=True)
# obj = {
#        'answer': 42,
#        'arr': [None, True, 3.14],
#        'truth': {
#            'coord': 'out there'
#        }
#    }
#
# r.jsonset('obj', Path.rootPath(), obj)
# # time.sleep(1)
# print(r.jsonget('obj',  Path.rootPath()))
