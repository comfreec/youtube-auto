#!/usr/bin/env python3
"""
스마트 가격 전략 시스템
지역별, 사용자별 맞춤 가격 및 할인 시스템
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import hashlib
import secrets

# Add the root directory to the path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
if root_dir not in sys.path:
    sys.path.append(root_dir)

class Currency(Enum):
    """통화 타입"""
    USD = "USD"
    KRW = "KRW"
    EUR = "EUR"
    JPY = "JPY"
    CNY = "CNY"

