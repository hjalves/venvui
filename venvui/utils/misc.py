# -*- coding: utf-8 -*-

import random
import string


def keygen(n=8):
    random.seed(1)
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))
