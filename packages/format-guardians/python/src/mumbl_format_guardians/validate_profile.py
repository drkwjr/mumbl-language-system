import json, sys
from pydantic import ValidationError
from mumbl_data_contracts.profiles import LanguageProfileV1

def validate_profile_json_str(s: str):
    obj = json.loads(s)
    LanguageProfileV1(**obj)
    return True
