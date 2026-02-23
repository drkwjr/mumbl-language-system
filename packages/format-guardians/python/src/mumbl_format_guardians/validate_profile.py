import json
import sys

from mumbl_data_contracts.profiles import LanguageProfileV1
from pydantic import ValidationError


def validate_profile_json_str(s: str):
    obj = json.loads(s)
    LanguageProfileV1(**obj)
    return True
