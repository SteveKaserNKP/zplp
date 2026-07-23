from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field

DEFINES = {}

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

@dataclass
class ZPL_Setup_Command:
    ...

@dataclass
class ZPL_Print_Width(ZPL_Setup_Command):
    width: int = 2
    operator: str = "^PW"

@dataclass
class ZPL_ZPL_Mode(ZPL_Setup_Command):
    mode: int = 2
    operator: str = "^SZ"

@dataclass
class ZPL_Dots_Per_MM(ZPL_Setup_Command):
    dots: str = "A"
    operator: str = "^JM"

@dataclass
class ZPL_Bitmap_Clear(ZPL_Setup_Command):
    should_clear: str = "Y"
    operator: str = "^MC"

@dataclass
class ZPL_Mirror_Image(ZPL_Setup_Command):
    should_mirror: str = "N"
    operator: str = "^PM"

@dataclass
class ZPL_Backfeed_Seq(ZPL_Setup_Command):
    backfeed_amount: ZPL_Backfeed_Amount
    operator: str = "~JS"

@dataclass
class ZPL_Reprint_After_Error(ZPL_Setup_Command):
    should_reprint_after_error: str = "Y"
    operator: str = "^JZ"

@dataclass
class ZPL_Label_Home(ZPL_Setup_Command):
    home: tuple[int, int] = (0, 0)
    operator: str = "^LH"

@dataclass
class ZPL_Reverse_Print(ZPL_Setup_Command):
    should_reverse_print: str = "N"
    operator: str = "^LR"

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

@dataclass
class ZPL_Field_Origin(ZPL_Field_Position):
    operator: str = "^FO"

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

@dataclass
class ZPL_Linear_Barcode_Config():
    module_width: int = 2
    bar_width_ratio: float = 3.0
    module_height: int = 10
    type: ZPL_Field_Type = ZPL_Field_Type.BARCODE
    barcode_type: ZPL_Barcode_Type = ZPL_Barcode_Type.LINEAR

class ZPL_Linear_Barcode_Code39(ZPL_Field):
    config: ZPL_Linear_Barcode_Config = ZPL_Linear_Barcode_Config()
    linear_barcode_type: ZPL_Linear_Barcode_Type = ZPL_Linear_Barcode_Type.CODE39
    orientation: ZPL_Field_Orientation = ZPL_Field_Orientation.NORMAL
    use_mod43_check_digit: str = "N"
    height: int = 1
    print_value_below_barcode: str = "Y"
    print_value_above_barcode: str = "N"
    operator: str = "^B3"

@dataclass
class ZPL_Graphic_Field(ZPL_Field):
    type: ZPL_Field_Type = ZPL_Field_Type.GRAPHIC

@dataclass
class ZPL_Graphic_Box_Field(ZPL_Graphic_Field):
    width: int = 1
    height: int = 1
    thickness: int = 1
    line_color: str = "B"
    deg_of_corner_rounding: int = 0
    graphic_type: ZPL_Graphic_Type = ZPL_Graphic_Type.BOX

@dataclass
class ZPL_Section:
    label: str
    fields: list[ZPL_Field] = field(default_factory=list)

@dataclass
class ZPL_Document:
    setup: list[ZPL_Setup_Command] = field(default_factory=list)
    sections: list[ZPL_Section] = field(default_factory=list)

class Line_Type(Enum):
    DEF = 0
    BLOCK_BEGIN = 1
    BLOCK_END = 2
    COMMENT = 3
    PARAMETER = 4

class Block_Type(Enum):
    DOCUMENT = 0
    SETUP = 1
    SECTION = 2
    FIELD = 3

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
    
def handle_def(line: str) -> None:
    line = line[4:]
    chunks = line.split(" ")
    var = chunks.pop(0)
    value = ''.join(chunks)
    if var in DEFINES:
        raise KeyError(f"Key with name {var} already exists!")
    DEFINES[var] = value