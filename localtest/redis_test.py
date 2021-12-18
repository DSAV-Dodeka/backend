import redis
from redis.commands.json.path import Path
import time

then = time.perf_counter()
d = {"hello": "world", "key": "value"}
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
print(r.json().get("d846be7bd6918f0e21cf43ecd644680b00c5d2ecbf97b1f3f4a9b16caf9c30fe"))
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
