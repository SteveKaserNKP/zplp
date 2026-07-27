from pathlib import Path
from decimal import Decimal
import json
from collections import OrderedDict

def get_file_data(fp: Path) -> list[str]:
    lines = []
    with open(str(fp), "r") as f:
        lines = f.readlines()
    return lines

def is_numeric(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False

def validate_numeric[T: (int, float)](
    val: T, 
    min_val: T, 
    max_val: T, 
    default_val: T,
    step_val: T | None = None  # Make step optional so it handles both your use cases
) -> tuple[bool, str, T]:
    
    # Cast all parameters safely to Decimal using their string values to prevent float artifacts
    v  = Decimal(str(val))
    mn = Decimal(str(min_val))
    mx = Decimal(str(max_val))
    
    # 1. Boundary Checks
    if v < mn:
        return (False, f"Value {val} is less than minimum value ({min_val})! Using the default_value: {default_val}", default_val)
    if v > mx:
        return (False, f"Value {val} is greater than maximum value ({max_val})! Using the default_value: {default_val}", default_val)
        
    # 2. Step Alignment Check (Only runs if a step value was actually provided)
    if step_val is not None:
        st = Decimal(str(step_val))
        if st != 0 and (v - mn) % st != 0:
            return (False, f"Value {val} is not a valid step between {min_val} and {max_val}! Using the default_value: {default_val}", default_val)
            
    return (True, "", val)

def validate_list[T: (int, float, str)](
    val: T, 
    options: list[T], 
    default_val: T
) -> tuple[bool, str, T]:
    if val not in options:
        # Note: used ', '.join(map(str, options)) to safely format numeric lists to text
        options_str = ", ".join(map(str, options))
        return (False, f"Value {val} not in the provided options: [{options_str}]. Using the default_value: {default_val}", default_val)
    return (True, "", val)


def get_file_encoding(fp: Path) -> str:
    with open(fp, "rb") as fb:
        heading = fb.read(4)
    if heading.startswith(b"\xff\xfe") or heading.startswith(b"\xfe\xff"):
        # UTF-16 BOM detected ('ÿþ' or 'þÿ')
        return "utf-16"
    elif heading.startswith(b"\xef\xbb\xbf"):
        # UTF-8 BOM detected ('ï»¿')
        return "utf-8-sig"
    else:
        # No BOM detected; fallback to standard UTF-8
        return "utf-8"
    
def read_json_file(fp: Path) -> OrderedDict:
    if not fp.exists():
        print(f"fp does not exist: {fp.absolute()}")
    if not fp.is_file():
        print(f"fp is not a file: {fp.absolute()}")
    return json.loads(
        fp.read_text(encoding=get_file_encoding(fp)),
        object_pairs_hook=OrderedDict)