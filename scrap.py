import datetime

import requests
import json

from dateutil.relativedelta import relativedelta, MO

# sometime = datetime.datetime.strptime('24052010', "%d%m%Y").date()
# last_monday = str(sometime + relativedelta(weekday=MO(-2)))
# print(last_monday)
#
# for x in range(50):
#     print(sometime)
#     sometime += datetime.timedelta(days=1)

num1 = 1
num2 = 2
num3 = 3
num4 = 4

var = min(num2, num4, num1, num3)

print(var)