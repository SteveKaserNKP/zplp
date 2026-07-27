from enum import Enum
from dataclasses import dataclass, field
import requests
import shutil
from utils import *

class ZPL_Operator(Enum):
    CARET = 0
    TILDE = 1

class ZPLP_Field_Type(Enum):
    UNKNOWN = 0
    TEXT = 1
    BARCODE = 2
    GRAPHIC = 3
    SETUP = 4

class ZPLP_Field_Origin_Mnemonic(Enum):
    FT = 0
    FO = 1

class Line_Type(Enum):
    DEF = 0
    BLOCK_BEGIN = 1
    BLOCK_END = 2
    COMMENT = 3
    ZPLP_COMMAND = 4

class Block_Type(Enum):
    DOCUMENT = 0
    SECTION = 1
    FIELD = 2

class ZPLP_Parameter_Type(Enum):
    STRING = 0
    INTEGER = 1
    FLOAT = 2

class ZPLP_Parameter_Validation_Type(Enum):
    NONE = 0
    RANGE = 1
    LIST = 2

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
    type_text: str = ""

@dataclass
class Block_End_Line(Line):
    block_type: Block_Type
    label: str = ""

@dataclass
class ZPLP_Command_Line(Line):
    command_name: str
    arg: str

@dataclass(kw_only=True)
class ZPLP_Parameter_Schema:
    name: str
    type: ZPLP_Parameter_Type
    validation: ZPLP_Parameter_Validation_Type

@dataclass(kw_only=True)
class ZPLP_String_Parameter_Schema(ZPLP_Parameter_Schema):
    default_value: str
    valid_options: list[str] = field(default_factory=list)
    type: ZPLP_Parameter_Type = ZPLP_Parameter_Type.STRING

@dataclass(kw_only=True)
class ZPLP_Integer_Parameter_Schema(ZPLP_Parameter_Schema):
    default_value: int
    min_val: int = 0
    max_val: int = 0
    step: int = 0
    type: ZPLP_Parameter_Type = ZPLP_Parameter_Type.INTEGER
    valid_options: list[int] = field(default_factory=list)

@dataclass(kw_only=True)
class ZPLP_Float_Parameter_Schema(ZPLP_Parameter_Schema):
    default_value: float
    type: ZPLP_Parameter_Type = ZPLP_Parameter_Type.FLOAT
    min_val: float = 0
    max_val: float = 0
    step: float = 0
    valid_options: list[float] = field(default_factory=list)

@dataclass(kw_only=True)
class ZPLP_Parameter_Value[T: (int, float, str)]:
    schema: ZPLP_Parameter_Schema
    value: T
    var_name: str = ""
    is_valid: bool = True
    error_message: str = ""

    @staticmethod
    def from_raw_string(schema: ZPLP_Parameter_Schema, raw_value: str) -> "ZPLP_Parameter_Value":
        """Parses and validates a raw string into a typed ZPLP_Parameter_Value instance."""
        
        # 1. Handle completely empty parameter fields (e.g. tracking missing args like ^FO50,,100)
        if len(raw_value.strip()) == 0:
            default_val = getattr(schema, "default_value", "")
            return ZPLP_Parameter_Value(
                schema=schema, 
                value=default_val, 
                is_valid=False, 
                error_message="Value cannot be blank! Default applied."
            )

        var_name = ""
        if raw_value.startswith("{") and raw_value.endswith("}"):
            if "::" not in raw_value:
                raise ValueError(f"Variable not formatted correct. Should take the form of \"{{VAR_NAME}}::{{DEFAULT_VALUE}}\"")
            var_name, raw_value = raw_value[1:-1].split("::")

        # 2. Match against structural schemas to extract and validate values
        match schema:
            case ZPLP_String_Parameter_Schema() as s:
                if s.validation == ZPLP_Parameter_Validation_Type.NONE:
                    return ZPLP_Parameter_Value(schema=s, value=raw_value, var_name=var_name)
                
                elif s.validation == ZPLP_Parameter_Validation_Type.LIST:
                    is_ok, err, final_val = validate_list(raw_value, s.valid_options, s.default_value)
                    return ZPLP_Parameter_Value(schema=s, value=final_val, is_valid=is_ok, error_message=err, var_name=var_name)
                
                else:
                    raise ValueError(f"Invalid validation type for String: {s.validation}")

            case ZPLP_Integer_Parameter_Schema() as s:
                try:
                    parsed_int = int(raw_value)
                except ValueError:
                    return ZPLP_Parameter_Value(
                        schema=s, value=s.default_value, is_valid=False, 
                        error_message=f"Could not parse '{raw_value}' as an integer. Default applied."
                    )

                if s.validation == ZPLP_Parameter_Validation_Type.NONE:
                    return ZPLP_Parameter_Value(schema=s, value=parsed_int, var_name=var_name)
                
                elif s.validation == ZPLP_Parameter_Validation_Type.LIST:
                    is_ok, err, final_val = validate_list(parsed_int, s.valid_options, s.default_value)
                    return ZPLP_Parameter_Value(schema=s, value=final_val, is_valid=is_ok, error_message=err, var_name=var_name)
                
                elif s.validation == ZPLP_Parameter_Validation_Type.RANGE:
                    step = s.step if s.step > 0 else None
                    is_ok, err, final_val = validate_numeric(parsed_int, s.min_val, s.max_val, s.default_value, step_val=step)
                    return ZPLP_Parameter_Value(schema=s, value=final_val, is_valid=is_ok, error_message=err, var_name=var_name)
                
                else:
                    raise ValueError(f"Invalid validation type for Integer: {s.validation}")

            case ZPLP_Float_Parameter_Schema() as s:
                try:
                    parsed_float = float(raw_value)
                except ValueError:
                    return ZPLP_Parameter_Value(
                        schema=s, value=s.default_value, is_valid=False, 
                        error_message=f"Could not parse '{raw_value}' as a float. Default applied.", var_name=var_name
                    )

                if s.validation == ZPLP_Parameter_Validation_Type.NONE:
                    return ZPLP_Parameter_Value(schema=s, value=parsed_float, var_name=var_name)
                
                elif s.validation == ZPLP_Parameter_Validation_Type.LIST:
                    is_ok, err, final_val = validate_list(parsed_float, s.valid_options, s.default_value)
                    return ZPLP_Parameter_Value(schema=s, value=final_val, is_valid=is_ok, error_message=err, var_name=var_name)
                
                elif s.validation == ZPLP_Parameter_Validation_Type.RANGE:
                    step = s.step if s.step > 0 else None
                    is_ok, err, final_val = validate_numeric(parsed_float, s.min_val, s.max_val, s.default_value, step_val=step)
                    return ZPLP_Parameter_Value(schema=s, value=final_val, is_valid=is_ok, error_message=err, var_name=var_name)
                
                else:
                    raise ValueError(f"Invalid validation type for Float: {s.validation}")

            case _:
                raise ValueError(f"Unhandled ZPLP_Parameter_Schema type: {type(schema).__name__}")

@dataclass(kw_only=True)
class ZPLP_Command_Schema:
    operator: ZPL_Operator
    mnemonic: str
    keyword: str
    parameters: list[ZPLP_Parameter_Schema] = field(default_factory=list)
    parameter_separator_char: str = ","

@dataclass(kw_only=True)
class ZPLP_Command_Value:
    schema: ZPLP_Command_Schema
    line_number: int
    parameters: list[ZPLP_Parameter_Value] = field(default_factory=list)

    def get_parameter(self, name: str) -> ZPLP_Parameter_Value:
        param = [p for p in self.parameters if p.schema.name == name]
        if len(param) == 0:
            raise ValueError(f"Could not find a parameter called {name} in ZPLP_Field!")
        return param[0]

    def get_operator(self) -> str:
        if self.schema.operator == ZPL_Operator.CARET:
            return "^"
        if self.schema.operator == ZPL_Operator.TILDE:
            return "~"
        raise ValueError(f"Unhandled operator: {self.schema.operator}")

    def get_zpl(self) -> str:
        zpl = f"  {self.get_operator()}{self.schema.mnemonic}"
        for i, p in enumerate(self.parameters):
            if i == 0:
                zpl += f"{p.value}"
            else:
                zpl += f",{p.value}"
        zpl += "\n"
        return zpl

@dataclass
class ZPLP_Field:
    label: str
    active: bool = True
    type: ZPLP_Field_Type = ZPLP_Field_Type.UNKNOWN
    field_origin_mnemonic: ZPLP_Field_Origin_Mnemonic = ZPLP_Field_Origin_Mnemonic.FO
    commands: list[ZPLP_Command_Value] = field(default_factory=list)

    def get_command(self, kw: str) -> ZPLP_Command_Value:
        command = [c for c in self.commands if c.schema.keyword == kw]
        if len(command) == 0:
            raise ValueError(f"Could not find a command called {kw} in ZPLP_Field!")
        return command[0]

@dataclass
class ZPLP_Setup_Field(ZPLP_Field):
    type: ZPLP_Field_Type = ZPLP_Field_Type.SETUP

@dataclass
class ZPLP_Text_Field(ZPLP_Field):
    font: ZPLP_Command_Value | None = None
    text: ZPLP_Command_Value | None = None
    type: ZPLP_Field_Type = ZPLP_Field_Type.TEXT
    field_origin_mnemonic: ZPLP_Field_Origin_Mnemonic = ZPLP_Field_Origin_Mnemonic.FT

@dataclass
class ZPLP_Linear_Barcode_Code39_Field(ZPLP_Field):
    linear_barcode_config: ZPLP_Command_Value | None = None
    code39_config: ZPLP_Command_Value | None = None
    text: ZPLP_Command_Value | None = None
    type: ZPLP_Field_Type = ZPLP_Field_Type.BARCODE
    field_origin_mnemonic: ZPLP_Field_Origin_Mnemonic = ZPLP_Field_Origin_Mnemonic.FO

@dataclass
class ZPLP_Graphic_Box_Field(ZPLP_Field):
    box: ZPLP_Command_Value | None = None
    type: ZPLP_Field_Type = ZPLP_Field_Type.GRAPHIC
    field_origin_mnemonic: ZPLP_Field_Origin_Mnemonic = ZPLP_Field_Origin_Mnemonic.FO

@dataclass
class ZPL_Section:
    label: str = ""
    active: bool = True
    fields: list[ZPLP_Field] = field(default_factory=list)

    def get_active_field(self) -> ZPLP_Field | None:
        if len(self.fields) > 0:
            fields = [f for f in self.fields if f.active]
            if len(fields) > 0:
                return fields[-1]
        return None

@dataclass
class ZPL_Document:
    sections: list[ZPL_Section] = field(default_factory=list)

    def get_active_section(self) -> ZPL_Section | None:
        if len(self.sections) > 0:
            sections = [s for s in self.sections if s.active]
            if len(sections) > 0:
                return sections[-1]
        return None

@dataclass
class ZPLP_File:
    zplp_file_path: str
    commands_file_path: str
    document: ZPL_Document | None = None
    commands: list[ZPLP_Command_Schema] = field(default_factory=list)
    lines: list[Line] = field(default_factory=list)
    defines: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        zplp_fp = Path(self.zplp_file_path)
        ok, msg = self._validate_file_(zplp_fp)
        if not ok:
            raise ValueError(msg)
        commands_fp = Path(self.commands_file_path)
        ok, msg = self._validate_file_(zplp_fp)
        if not ok:
            raise ValueError(msg)
        self.load_commands(commands_fp)
        self.lex_file(zplp_fp)
        self.parse_file()

    def _validate_file_(self, fp: Path) -> tuple[bool, str]:
        if not fp.is_file():
            return (False, f"{fp} is not a file!")
        if fp.suffix not in [".zplp", ".json"]:
            return (False, f"{fp} is not a valid file type!")
        return (True, "")

    def load_commands(self, fp: Path) -> None:
        json_commands = read_json_file(fp)
        for command_name in json_commands:
            command = json_commands[command_name]
            if command["operator"] == "^":
                op = ZPL_Operator.CARET
            elif command["operator"] == "~":
                op = ZPL_Operator.TILDE
            else:
                raise ValueError(f"{command["operator"]} is not a valid operator!")
            mn = command["mnemonic"]
            kw = command_name
            params: list[ZPLP_Parameter_Schema] = []
            for param in command["parameters"]:
                step = 0
                if "step" in param:
                    step = param["step"]
                match param["validation_type"]:
                    case "NONE": val_type = ZPLP_Parameter_Validation_Type.NONE
                    case "LIST": val_type = ZPLP_Parameter_Validation_Type.LIST
                    case "RANGE": val_type = ZPLP_Parameter_Validation_Type.RANGE
                    case _: raise ValueError(f"Invalid ZPLP_Parameter_Validation_Type: {param["validation type"]}")
                match param["type"]:
                    case "INTEGER":
                        if param["validation_type"] == "RANGE":
                            p = ZPLP_Integer_Parameter_Schema(name=param["name"], default_value=int(param["default_value"]), min_val=int(param["min"]), max_val=int(param["max"]), step=int(step), validation=val_type)
                        elif param["validation_type"] == "LIST":
                            opts_int: list[int] = []
                            for opt in param["options"]:
                                if not is_numeric(opt):
                                    raise ValueError(f"Expected all options to be integers but {opt} cannot be converted to a number!")
                                opts_int.append(opt)
                            p = ZPLP_Integer_Parameter_Schema(name=param["name"], default_value=int(param["default_value"]), valid_options=opts_int, validation=val_type)
                        # elif param["validation_type"] == "VARIABLE":
                        #     ...
                        else:
                            raise ValueError(f"Unhandled validation type ({param["validation_type"]}) for parameter type ({param["type"]})")
                    case "FLOAT":
                        if param["validation_type"] == "RANGE":
                            p = ZPLP_Float_Parameter_Schema(name=param["name"], default_value=float(param["default_value"]), min_val=float(param["min"]), max_val=float(param["max"]), step=float(step), validation=val_type)
                        elif param["validation_type"] == "LIST":
                            opts_float: list[float] = []
                            for opt in param["options"]:
                                if not is_numeric(opt):
                                    raise ValueError(f"Expected all options to be integers but {opt} cannot be converted to a number!")
                                opts_float.append(opt)
                            p = ZPLP_Float_Parameter_Schema(name=param["name"], default_value=float(param["default_value"]), valid_options=opts_float, validation=val_type)
                        else:
                            raise ValueError(f"Unhandled validation type ({param["validation_type"]}) for parameter type ({param["type"]})")
                    case "STRING":
                        if param["validation_type"] == "LIST":
                            opts_str: list[str] = []
                            for opt in param["options"]:
                                opts_str.append(str(opt))
                            p = ZPLP_String_Parameter_Schema(name=param["name"], default_value=param["default_value"], valid_options=opts_str, validation=val_type)
                        elif param["validation_type"] == "NONE":
                            p = ZPLP_String_Parameter_Schema(name=param["name"], default_value=param["default_value"], validation=ZPLP_Parameter_Validation_Type.NONE)
                        else:
                            raise ValueError(f"Unhandled validation type ({param["validation_type"]}) for parameter type ({param["type"]})")
                    case _:
                        raise ValueError(f"Unhanlded ZPL Parameter Type: {param["type"]}")
                params.append(p)
            self.commands.append(ZPLP_Command_Schema(operator=op, mnemonic=mn, keyword=kw, parameters=params))

    def lex_file(self, fp: Path) -> None:
        lines = get_file_data(fp)
        for i, line in enumerate(lines):
            line = line.strip()
            if len(line) == 0:
                continue
            if line.startswith("DEF"):
                _, var, value = line.split(" ")
                self.lines.append(Def_Line(Line_Type.DEF, line, i+1, var, value))
            elif line.startswith("BEGIN_"):
                label = ""
                type_text = ""
                if line.startswith("BEGIN_DOCUMENT"):
                    block_type = Block_Type.DOCUMENT
                elif line.startswith("BEGIN_SECTION"):
                    block_type = Block_Type.SECTION
                    if "::" in line:
                        label = ''.join(line.split("::")[1:])
                elif line.startswith("BEGIN_FIELD"):
                    block_type = Block_Type.FIELD
                    if line.count("::") == 2:
                        _, type_text, label = line.split("::")
                else:
                    raise ValueError("Unhandled block type: %1", line)
                self.lines.append(Block_Begin_Line(Line_Type.BLOCK_BEGIN, line, i+1, block_type, label.strip(), type_text.strip()))
            elif line.startswith("END_"):
                if line.startswith("END_DOCUMENT"):
                    block_type = Block_Type.DOCUMENT
                elif line.startswith("END_SECTION"):
                    block_type = Block_Type.SECTION
                elif line.startswith("END_FIELD"):
                    block_type = Block_Type.FIELD
                else:
                    raise ValueError("Unhandled block type: %1", line)
                label = ""
                if ":" in line:
                    label = ''.join(line.split(":")[1:])
                self.lines.append(Block_End_Line(Line_Type.BLOCK_END, line, i+1, block_type, label))
            elif line.startswith("//"):
                self.lines.append(Line(Line_Type.COMMENT, line, i+1))
            else:
                first_space = line.index(" ")
                param = line[0:first_space].strip()
                value = line[first_space+1:].strip()
                self.lines.append(ZPLP_Command_Line(Line_Type.ZPLP_COMMAND, line, i+1, param, value))

    def parse_file(self):
        for line in self.lines:
            match line:
                case Def_Line():
                    self.parse_def_line(line)
                case Block_Begin_Line(): 
                    match line.block_type:
                        case Block_Type.DOCUMENT:
                            self.parse_begin_document(line)
                        case Block_Type.SECTION:
                            self.parse_begin_section(line)
                        case Block_Type.FIELD:
                            self.parse_begin_field(line)
                        case _:
                            raise ValueError(f"{self.zplp_file_path}:{line.number}: Unhandled block type: {line.text}")
                case Block_End_Line():
                    match line.block_type:
                        case Block_Type.DOCUMENT:
                            # nothing to do here
                            ...
                        case Block_Type.SECTION:
                            self.parse_end_section(line)
                        case Block_Type.FIELD:
                            self.parse_end_field(line)
                        case _:
                            raise ValueError(f"{self.zplp_file_path}:{line.number}: Unhandled block type: {line.text}")
                case ZPLP_Command_Line():
                    self.parse_zplp_command_line(line)
                case _:
                    ...

    def find_command_by_keyword(self, kw: str) -> ZPLP_Command_Schema | None:
        command = [c for c in self.commands if c.keyword == kw]
        if len(command) == 1:
            return command[0]
        if len(command) > 1:
            raise ValueError(f"More than 1 command found for keyword {kw}!")

    def parse_def_line(self, line: Def_Line) -> None:
        line.__class__ = Def_Line
        if line.var_name in self.defines:
            raise KeyError(f"Line {line.number}: {line.var_name} is already defined!")
        self.defines[line.var_name] = line.value

    def parse_begin_document(self, line: Block_Begin_Line):
        if line.block_type != Block_Type.DOCUMENT:
            raise ValueError(f"{self.zplp_file_path}{line.number}: Invalid block type ({line.block_type}) for parse_begin_document!")
        if self.document is not None:
            raise ValueError(f"{self.zplp_file_path}{line.number}: Nested documents are not allowed in a zplp file!")

        self.document = ZPL_Document()

    def parse_begin_section(self, line: Block_Begin_Line):
        if self.document is None:
            raise ValueError(f"{self.zplp_file_path}:{line.number}: Cannot start a section before opening a document!")
        if self.document.get_active_section() is not None:
            raise ValueError(f"{self.zplp_file_path}:{line.number}: Nested sections are not allowed!")
        
        if line.block_type != Block_Type.SECTION:
            raise ValueError(f"{self.zplp_file_path}{line.number}: Invalid block type ({line.block_type}) for parse_begin_section!")
        
        self.document.sections.append(ZPL_Section(line.label.strip()))

    def parse_end_section(self, line: Block_End_Line):
        if self.document is None:
            raise ValueError(f"{self.zplp_file_path}:{line.number}: Cannot end a section before opening a document!")
        section = self.document.get_active_section()
        if section is None:
            raise ValueError(f"{self.zplp_file_path}:{line.number}: No active section found to end!")
        
        if line.block_type != Block_Type.SECTION:
            raise ValueError(f"{self.zplp_file_path}:{line.number}: Invalid block type ({line.block_type}) for parse_end_section!")

        section.active = False

    def parse_begin_field(self, line: Block_Begin_Line):
        if self.document is None:
            raise ValueError(f"{self.zplp_file_path}:{line.number}: Cannot start a section before opening a document!")
        section = self.document.get_active_section()
        if section is None:
            raise ValueError(f"{self.zplp_file_path}:{line.number}: Cannot start a field before starting a section!")
        if section.get_active_field() is not None:
            raise ValueError(f"{self.zplp_file_path}:{line.number}: Nested fields are not allowed!")
        
        if line.block_type != Block_Type.FIELD:
            raise ValueError(f"{self.zplp_file_path}:{line.number}: Invalid block type ({line.block_type}) for parse_begin_field!")

        if len(line.label.strip()) == 0:
            raise ValueError(f"{self.zplp_file_path}:{line.number}: BEGIN_FIELD's label must not be blank!")

        if line.type_text == "TEXT":
            section.fields.append(ZPLP_Text_Field(line.label))
        elif line.type_text == "SETUP":
            section.fields.append(ZPLP_Setup_Field(line.label))
        elif line.type_text == "LINEAR_BARCODE_CODE39":
            section.fields.append(ZPLP_Linear_Barcode_Code39_Field(line.label))
        elif line.type_text == "GRAPHIC_BOX":
            section.fields.append(ZPLP_Graphic_Box_Field(line.label))
        else:
            raise ValueError(f"{self.zplp_file_path}:{line.number}: {line.type_text.strip()} is not a valid field type!")

    def parse_end_field(self, line: Block_End_Line):
        if self.document is None:
            raise ValueError(f"{self.zplp_file_path}:{line.number}: Cannot end a section before opening a document!")
        section = self.document.get_active_section()
        if section is None:
            raise ValueError(f"{self.zplp_file_path}:{line.number}: No active section found to end!")
        fld = section.get_active_field()
        if fld is None:
            raise ValueError(f"{self.zplp_file_path}:{line.number}: No active field found to end!")
        
        if line.block_type != Block_Type.FIELD:
            raise ValueError(f"{self.zplp_file_path}:{line.number}: Invalid block type ({line.block_type}) for parse_end_field!")

        fld.active = False

    def parse_zplp_command_line(self, line: ZPLP_Command_Line):
        if self.document is None:
            raise ValueError(f"{self.zplp_file_path}:{line.number}: Cannot start a section before opening a document!")
        section = self.document.get_active_section()
        if section is None:
            raise ValueError(f"{self.zplp_file_path}:{line.number}: No active section found to end!")
        fld = section.get_active_field()
        if fld is None:
            raise ValueError(f"{self.zplp_file_path}:{line.number}: Cannot add a command without a field!")

        command = self.find_command_by_keyword(line.command_name)
        if command is None:
            raise ValueError(f"{self.zplp_file_path}:{line.number}: Unsupported zplp command: {line.command_name}!")
        else:
            pv = self.parse_command_arguments(command, line.arg, line.number)
            fld.commands.append(pv)

    def parse_command_arguments(
        self,
        schema: ZPLP_Command_Schema, 
        raw_arguments_str: str, 
        line_number: int
    ) -> ZPLP_Command_Value:
        """
        Parses a raw ZPL arguments string into a fully validated ZPLP_Command_Value.
        Example input: raw_arguments_str="50,100,,Y"
        """
        # 1. Create a fresh command instance container linked back to its blueprint
        command_instance = ZPLP_Command_Value(schema=schema, line_number=line_number)
        
        # 2. Split the arguments string by commas. 
        # If the string is totally empty, treat it as an empty list instead of [""]
        if raw_arguments_str.startswith("*"):
            if raw_arguments_str[1:] not in self.defines:
                raise ValueError(f"{raw_arguments_str[1:]} is not defined!")
            raw_arguments_str = self.defines[raw_arguments_str[1:]]
        raw_tokens = raw_arguments_str.split(",") if raw_arguments_str.strip() else []
        if schema.keyword == "FONT":
            if len(raw_tokens[0]) == 2:
                font_name, orientation = raw_tokens[0]
                raw_tokens[0] = font_name
                raw_tokens.insert(1, orientation)
        tokens = []
        for token in raw_tokens:
            if token.strip().startswith("*"):
                if token.strip()[1:] not in self.defines:
                    raise ValueError(f"{token.strip()[1:]} is not defined!")
                token = self.defines[token.strip()[1:]]
            tokens.append(token)

        raw_tokens = tokens
        
        total_expected = len(schema.parameters)
        total_parsed = len(raw_tokens)
        
        # 3. Determine the maximum length we need to iterate over.
        # This guarantees we process ALL expected schema parameters, even if the ZPL line cuts short.
        max_loops = max(total_expected, total_parsed)
        
        for index in range(max_loops):
            # Case A: The ZPL line provided more arguments than the schema allows
            if index >= total_expected:
                extra_token = raw_tokens[index].strip()
                if extra_token: # Only care if the extra parameter actually contains data
                    print(
                        f"Warning [Line {line_number}]: Command '{schema.mnemonic}' "
                        f"received extra unexpected argument '{extra_token}' at position {index + 1}. Skipping."
                    )
                continue
                
            # Grab the current rule definition for this position
            param_schema = schema.parameters[index]
            
            # Case B: The ZPL line omitted trailing parameters (the line ended early)
            if index >= total_parsed:
                raw_token = ""  # Force an empty string to trigger schema default values
                
            # Case C: Standard extraction
            else:
                raw_token = raw_tokens[index].strip()
                
            # 4. Delegate token execution to your static parameter factory
            param_value = ZPLP_Parameter_Value.from_raw_string(param_schema, raw_token)
            
            # 5. Handle any downstream validation flags flagged by the factory
            if not param_value.is_valid:
                print(
                    f"Validation Notice [Line {line_number}, Param '{param_schema.name}']: "
                    f"{param_value.error_message}"
                )
                
            # 6. Append the verified node container to the command instance data pool
            command_instance.parameters.append(param_value)
            
        return command_instance

    def generate_zpl(self, testing_zpl: bool) -> str:
        if self.document is None:
            raise ValueError("Document is blank!")
        if self.document.sections is None:
            raise ValueError("Documente has no sections!")
        zpl = "^XA\n"
        for section in self.document.sections:
            for f in section.fields:
                zpl += f"^FX{f.label}\n"
                if f.type == ZPLP_Field_Type.SETUP:
                    for c in f.commands:
                        zpl += c.get_zpl()
                elif f.type == ZPLP_Field_Type.TEXT:
                    pos = f.get_command("POSITION")
                    just = f.get_command("JUSTIFICATION")
                    zpl += f"  ^FT{pos.get_parameter("x-pos").value},{pos.get_parameter("y-pos").value},{just.get_parameter("justification").value}\n"
                    font = f.get_command("FONT")
                    zpl += f"  ^A{font.get_parameter("font name").value}{font.get_parameter("orientation").value},{font.get_parameter("height").value},{font.get_parameter("width").value}\n"
                    text = f.get_command("TEXT")
                    text_param = text.get_parameter("text")
                    if testing_zpl or text_param.var_name == "":
                        zpl += f"  ^FD{text.get_parameter("text").value}\n"
                    else:
                        zpl += f"  ^FD{{{text.get_parameter("text").var_name}}}\n"
                elif f.type == ZPLP_Field_Type.BARCODE:
                    pos = f.get_command("POSITION")
                    just = f.get_command("JUSTIFICATION")
                    zpl += f"  ^FO{pos.get_parameter("x-pos").value},{pos.get_parameter("y-pos").value},{just.get_parameter("justification").value}\n"
                    zpl += f.get_command("LINEAR_BARCODE_CONFIG").get_zpl()
                    zpl += f.get_command("CODE39_CONFIG").get_zpl()
                    text = f.get_command("TEXT")
                    text_param = text.get_parameter("text")
                    if testing_zpl or text_param.var_name == "":
                        zpl += f"  ^FD{text.get_parameter("text").value}\n"
                    else:
                        zpl += f"  ^FD{{{text.get_parameter("text").var_name}}}\n"
                elif f.type == ZPLP_Field_Type.GRAPHIC:
                    pos = f.get_command("POSITION")
                    just = f.get_command("JUSTIFICATION")
                    zpl += f"  ^FO{pos.get_parameter("x-pos").value},{pos.get_parameter("y-pos").value},{just.get_parameter("justification").value}\n"
                    zpl += f.get_command("BOX").get_zpl()
                zpl += "^FS\n"
        zpl += "^XZ"
        return zpl

    def get_png(self, zpl: str) -> None:
        url = 'http://api.labelary.com/v1/printers/8dpmm/labels/2.5x4/0/'
        files = {'file' : zpl}
        response = requests.post(url, files = files, stream = True)
        # headers = {'Accept' : 'application/pdf'} # omit this line to get PNG images back
        # response = requests.post(url, headers = headers, files = files, stream = True)

        if response.status_code == 200:
            response.raw.decode_content = True
            with open('label.png', 'wb') as out_file: # change file name for PNG images
                shutil.copyfileobj(response.raw, out_file)
        else:
            print('Error: ' + response.text)

