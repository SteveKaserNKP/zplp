from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field

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

def validate_min_max_int(val: int, min_val: int, max_val: int, default_val: int) -> tuple[bool, str, int]:
    if val < min_val:
        return (False, f"Value {val} is less than minimum value ({min_val})!", default_val)
    if val > max_val:
        return (False, f"Value {val} is greater than minimum value ({min_val})!", default_val)
    return (True, "", val)

def validate_min_max_float(val: float, min_val: float, max_val: float, default_val: float) -> tuple[bool, str, float]:
    if val < min_val:
        return (False, f"Value {val} is less than minimum value ({min_val})!", default_val)
    if val > max_val:
        return (False, f"Value {val} is greater than minimum value ({min_val})!", default_val)
    return (True, "", val)

def validate_min_max_step_int(val: int, min_val: int, max_val: int, step_val: int, default_val: int) -> tuple[bool, str, int]:
    if val < min_val:
        return (False, f"Value {val} is less than minimum value ({min_val})!", default_val)
    if val > max_val:
        return (False, f"Value {val} is greater than minimum value ({min_val})!", default_val)
    # TODO: figure out how to determine if the step is being respected
    return (True, "", val)

def validate_min_max_step_float(val: float, min_val: float, max_val: float, step_val: float, default_val: float) -> tuple[bool, str, float]:
    if val < min_val:
        return (False, f"Value {val} is less than minimum value ({min_val})!", default_val)
    if val > max_val:
        return (False, f"Value {val} is greater than minimum value ({min_val})!", default_val)
    # TODO: figure out how to determine if the step is being respected
    return (True, "", val)

def validate_list(val: str, options: list[str], default_val: str) -> tuple[bool, str, str]:
    if val not in options:
        return (False, f"Value {val} not in the provided options: {''.join(options)}", default_val)
    return (True, "", val)

class ZPL_Operator(Enum):
    CARET = 0
    TILDE = 1

class ZPL_Field_Type(Enum):
    TEXT = 0
    BARCODE = 1
    GRAPHIC = 2

class ZPL_Field_Orientation(Enum):
    NORMAL = 0
    ROTATED = 1
    INVERTED = 2
    BOTTOM = 3

class ZPL_Graphic_Type(Enum):
    BOX = 0

class ZPL_Backfeed_Amount(Enum):
    A = 0
    B = 1
    NORMAL = 2
    O = 3
    BF10 = 4
    BF20 = 5
    BF30 = 6
    BF40 = 7
    BF50 = 8
    BF60 = 9
    BF70 = 10
    BF80 = 11
    BF90 = 12

class ZPL_Barcode_Type(Enum):
    MULTI_DIM = 0
    LINEAR = 1
    POSTAL = 2

class ZPL_Linear_Barcode_Type(Enum):
    CODE39 = 0

class Line_Type(Enum):
    DEF = 0
    BLOCK_BEGIN = 1
    BLOCK_END = 2
    COMMENT = 3
    PARAMETER = 4

class Block_Type(Enum):
    DOCUMENT = 0
    SECTION = 1
    FIELD = 2

class ZPL_Parameter_Type(Enum):
    STRING = 0
    INTEGER = 1
    FLOAT = 2

class ZPL_Parameter_Validation_Type(Enum):
    NONE = 0
    MIN_MAX = 1
    MIN_MAX_STEP = 2
    LIST = 3
    COMMAND = 4

@dataclass(kw_only=True)
class ZPL_Parameter:
    name: str
    type: ZPL_Parameter_Type
    validation: ZPL_Parameter_Validation_Type

@dataclass
class ZPL_String_Parameter(ZPL_Parameter):
    default_value: str
    type: ZPL_Parameter_Type = ZPL_Parameter_Type.STRING
    validation: ZPL_Parameter_Validation_Type = ZPL_Parameter_Validation_Type.LIST
    valid_options: list[str] = field(default_factory=list)

@dataclass
class ZPL_Integer_Parameter(ZPL_Parameter):
    default_value: int
    type: ZPL_Parameter_Type = ZPL_Parameter_Type.INTEGER
    min: int = 0
    max: int = 0
    valid_options: list[int] = field(default_factory=list)

@dataclass
class ZPL_Float_Parameter(ZPL_Parameter):
    default_value: float
    type: ZPL_Parameter_Type = ZPL_Parameter_Type.FLOAT
    min: int = 0
    max: int = 0
    valid_options: list[float] = field(default_factory=list)

@dataclass(kw_only=True)
class ZPL_Command:
    operator: ZPL_Operator
    mnemonic: str
    keyword: str
    parameters: list[ZPL_Parameter] = field(default_factory=list)

@dataclass
class ZPL_Font:
    name: str
    orientation: ZPL_Field_Orientation
    height: int = 10
    width: int = 10

@dataclass
class ZPL_Text:
    variable_name: str
    value: str

@dataclass 
class ZPL_Field_Position:
    x: int = 0
    y: int = 0
    z: int = 0

# @dataclass
# class ZPL_Field_Origin(ZPL_Field_Position):
#     operator: str = "^FO"

@dataclass
class ZPL_Text_Field_Origin(ZPL_Field_Position):
    operator: str = "^FT"

@dataclass
class ZPL_Field:
    label: str
    position: ZPL_Field_Position

@dataclass
class ZPL_Text_Field(ZPL_Field):
    font: ZPL_Font
    text: ZPL_Text
    type: ZPL_Field_Type = ZPL_Field_Type.TEXT

# @dataclass
# class ZPL_Linear_Barcode_Config():
#     module_width: int = 2
#     bar_width_ratio: float = 3.0
#     module_height: int = 10
#     type: ZPL_Field_Type = ZPL_Field_Type.BARCODE
#     barcode_type: ZPL_Barcode_Type = ZPL_Barcode_Type.LINEAR

# class ZPL_Linear_Barcode_Code39(ZPL_Field):
#     config: ZPL_Linear_Barcode_Config = ZPL_Linear_Barcode_Config()
#     linear_barcode_type: ZPL_Linear_Barcode_Type = ZPL_Linear_Barcode_Type.CODE39
#     orientation: ZPL_Field_Orientation = ZPL_Field_Orientation.NORMAL
#     use_mod43_check_digit: str = "N"
#     height: int = 1
#     print_value_below_barcode: str = "Y"
#     print_value_above_barcode: str = "N"
#     operator: str = "^B3"

# @dataclass
# class ZPL_Graphic_Field(ZPL_Field):
#     type: ZPL_Field_Type = ZPL_Field_Type.GRAPHIC

# @dataclass
# class ZPL_Graphic_Box_Field(ZPL_Graphic_Field):
#     width: int = 1
#     height: int = 1
#     thickness: int = 1
#     line_color: str = "B"
#     deg_of_corner_rounding: int = 0
#     graphic_type: ZPL_Graphic_Type = ZPL_Graphic_Type.BOX

@dataclass
class ZPL_Section:
    label: str
    fields: list[ZPL_Field] = field(default_factory=list)

@dataclass
class Line:
    type: Line_Type
    text: str
    number: int

@dataclass
class Def_Line(Line):
    var_name: str
    value: str

@dataclass
class Block_Begin_Line(Line):
    block_type: Block_Type
    label: str = ""

@dataclass
class Block_End_Line(Line):
    block_type: Block_Type
    label: str = ""

@dataclass
class Parameter_Line(Line):
    param_name: str
    value: str

@dataclass
class Lexer:
    file_path: Path
    lines: list[Line] = field(default_factory=list)

@dataclass
class ZPL_Document:
    sections: list[ZPL_Section] = field(default_factory=list)
    defines: dict[str, str] = field(default_factory=dict)

    def parse_def_line(self, line: Def_Line) -> None:
        line.__class__ = Def_Line
        if line.var_name in self.defines:
            raise KeyError(f"Line {line.number}: {line.var_name} is already defined!")
        self.defines[line.var_name] = line.value

    def parse_begin_document_line(self, line: Block_Begin_Line) -> None:
        ...