from utils import *

def handle_setup(doc: ZPL_Document, line: str, lines: list[str]) -> tuple[ZPL_Document, list[str]]:
    while len(lines) > 0:
        line = lines.pop(0)
        if line.startswith("//"):
            continue
        if line.startswith("END_SETUP"):
            break
        chunks = line.split(" ")
        if line.startswith("PRINT_WIDTH"):
            if len(chunks) > 1:
                if not is_numeric(chunks[1]):
                    raise ValueError(f"Expected argument for PRINT_WIDTH to be numeric, but got {chunks[1]}")
                doc.setup.append(ZPL_Print_Width(int(chunks[1])))
            else:
                doc.setup.append(ZPL_Print_Width())
        elif line.startswith("ZPL_MODE"):
            if len(chunks) > 1:
                if not is_numeric(chunks[1]):
                    raise ValueError(f"Expected argument for ZPL_MODE to be numeric, but got {chunks[1]}")
                doc.setup.append(ZPL_ZPL_Mode(int(chunks[1])))
            else:
                doc.setup.append(ZPL_ZPL_Mode())
        elif line.startswith("DOTS_PER_MM"):
            if len(chunks) > 1:
                if chunks[1] not in ["A", "B"]:
                    raise ValueError(f"Expected argument for DOTS_PER_MM to be either 'A' or 'B', but got {chunks[1]}")
                doc.setup.append(ZPL_Dots_Per_MM(chunks[1]))
            else:
                doc.setup.append(ZPL_Dots_Per_MM())
        elif line.startswith("BITMAP_CLEAR"):
            if len(chunks) > 1:
                if chunks[1] not in ["Y", "N"]:
                    raise ValueError(f"Expected argument for BITMAP_CLEAR to be either 'Y' or 'N', but got {chunks[1]}")
                doc.setup.append(ZPL_Bitmap_Clear(chunks[1]))
            else:
                doc.setup.append(ZPL_Bitmap_Clear())
        else:
            raise ValueError(f"Unhandled Setup property: {line}")
    
    return (doc, lines)

def handle_section(doc: ZPL_Document, line: str, lines: list[str]) -> tuple[ZPL_Document, list[str]]:
    if ":" not in line:
        raise ValueError("BEGIN_SECTION does not have a label!")
    chunks = line.split(":")
    if len(chunks[1]) == 0:
        raise ValueError("BEGIN_SECTION's label is blank!")        
    section = ZPL_Section(chunks[1])
    while len(lines) > 0:
        line = lines.pop(0)
        if line.startswith("//"):
            continue
        if line.startswith("END_SECTION"):
            break
        if line.startswith("BEGIN_SECTION"):
            raise ValueError("Sections are not allowed to contain other Sections...for now...")
        if line.startswith("BEGIN_FIELD"):
            if ":" not in line:
                raise ValueError("BEGIN_FIELD does not have a label!")
            chunks = line.split(":")
            if len(chunks[1]) == 0:
                raise ValueError("BEGIN_FIELD's label is blank!")
            fld_label = chunks[1]
            fld_type = None
            fld_pos = None
            fld_font = None
            fld_text = None
            fld_bc_type = None
            fld_bc_config = None
            fld_bc_type_config = None
            fld_box_config = None
            while len(lines) > 0:
                line = lines.pop(0)
                if line.startswith("TYPE"):
                    if " " not in line:
                        raise ValueError("No argument found for TYPE field!")
                    chunks = line.split(" ")
                    if len(chunks[1]) == 0:
                        raise ValueError("TYPE's argument is blank!")
                    if chunks[1] == "TEXT": fld_type = ZPL_Field_Type.TEXT
                    elif chunks[1] == "BARCODE": fld_type = ZPL_Field_Type.BARCODE
                    elif chunks[1] == "GRAPHIC": fld_type = ZPL_Field_Type.GRAPHIC
                    else: raise ValueError(f"Invalid field TYPE: {chunks[1]}")
                elif line.startswith("POSITION"):
                    if " " not in line:
                        raise ValueError("No argument found for POSITION field!")
                    chunks = line.split(" ")
                    if len(chunks[1]) == 0:
                        raise ValueError("POSITION's arguments are blank!")
                    args = ''.join(chunks[1:])
                    if "," not in args:
                        raise ValueError("Comma not found in POSITION's arguments")
                    if args.count(",") > 2:
                        raise ValueError(f"Expected at most 3 arguments but found {args.count(",")}")
                    args = args.split(",")
                    fld_pos = ZPL_Field_Position()
                    for i, def_val in enumerate(args):
                        if def_val.startswith("*"):
                            def_val = def_val[1:]
                            if def_val not in DEFINES:
                                raise ValueError(f"{def_val} not defined!")
                            if not is_numeric(DEFINES[def_val]):
                                raise ValueError(f"Value for {def_val} ({DEFINES[def_val]}) is not a number!")
                            if i == 0: fld_pos.x = int(DEFINES[def_val])
                            elif i == 1: fld_pos.y = int(DEFINES[def_val])
                            elif i == 2: fld_pos.z = int(DEFINES[def_val])
                        else:
                            if not is_numeric(def_val):
                                raise ValueError(f"{def_val} is not a number. Arguments for POSITION must be numbers or references to DEFs!")
                            if i == 0: fld_pos.x = int(def_val)
                            elif i == 1: fld_pos.y = int(def_val)
                            elif i == 2: fld_pos.z = int(def_val)
                elif line.startswith("FONT"):
                    if " " not in line:
                        raise ValueError("No argument found for FONT field!")
                    chunks = line.split(" ")
                    if len(chunks[1]) == 0:
                        raise ValueError("FONT's arguments are blank!")
                    args = ''.join(chunks[1:])
                    if args.startswith("*"):
                        args = args[1:]
                        if args not in DEFINES:
                            raise ValueError(f"{args} not defined!")
                        def_val = DEFINES[args]
                        args = def_val
                    else:
                        args = ''.join(chunks[1:])
                    args_count = args.count(",")+1
                    if args_count == 0:
                        raise ValueError("FONT expects at least 3 arguments, but none were provided!")
                    if args_count < 2:
                        raise ValueError(f"FONT expects at least 3 arguments, but only found {args_count}!")
                    if args_count > 3:
                        raise ValueError(f"FONT expects at most 3 arguments, but found {args_count}!")
                    font_name = ""
                    font_orientation = ZPL_Field_Orientation.NORMAL
                    font_height = 10
                    font_width = 10
                    for i, arg in enumerate(args.split(",")):
                        if i == 0:
                            if len(arg) == 2:
                                font_name, orientation = arg
                                if orientation == "R": font_orientation = ZPL_Field_Orientation.ROTATED
                                elif orientation == "I": font_orientation = ZPL_Field_Orientation.INVERTED
                                elif orientation == "B": font_orientation = ZPL_Field_Orientation.BOTTOM
                                else: raise ValueError(f"Invalid font orientaion value: {orientation}!")
                            else:
                                font_name = arg
                            if font_name not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789':
                                raise ValueError(f'Invalid font name: {font_name}')
                        elif i == 1:
                            if not is_numeric(arg):
                                raise ValueError(f"Invalid height value: {arg}!")
                            font_height = int(arg)
                        elif i == 2:
                            if not is_numeric(arg):
                                raise ValueError(f"Invalid height value: {arg}!")
                            font_width = int(arg)
                    fld_font = ZPL_Font(font_name, font_orientation, font_height, font_width)
                elif line.startswith("TEXT"):
                    if " " not in line:
                        raise ValueError("No argument found for TEXT field!")
                    chunks = line.split(" ")
                    if len(chunks[1]) == 0:
                        raise ValueError("TEXT's argument is blank!")
                    arg = ' '.join(chunks[1:])
                    if arg.startswith("{"):
                        if not arg.endswith("}"):
                            raise ValueError("TEXT argument started with open curly brace but did not end with a closed curly brace!")
                        arg = arg[1:-1].strip()
                        if "::" not in arg:
                            raise ValueError("Default text not found in TEXT argument for placeholder!")
                        var_name, default_val = arg.split("::")
                        fld_text = ZPL_Text(var_name, default_val)
                    elif arg.startswith("*"):
                        if arg not in DEFINES:
                            raise ValueError(f"{arg} not defined!")
                        fld_text = ZPL_Text("", DEFINES[arg])
                    else:
                        fld_text = ZPL_Text("", arg)
                elif line.startswith("LINEAR_BARCODE_CONFIG"):
                    if " " not in line:
                        raise ValueError("No argument found for LINEAR_BARCODE_CONFIG field!")
                    chunks = line.split(" ")
                    if len(chunks[1]) == 0:
                        raise ValueError("LINEAR_BARCODE_CONFIG's argument is blank!")
                    arg = ''.join(chunks[1:])
                    if arg.startswith("*"):
                        arg = arg[1:]
                        if arg not in DEFINES:
                            raise ValueError(f"{arg} not defined!")
                        args = DEFINES[arg]
                    else:
                        args = arg
                    args_count = args.count(",")+1
                    if args_count == 0:
                        raise ValueError("LINEAR_BARCODE_CONFIG expects at least 3 arguments, but none were provided!")
                    if args_count < 2:
                        raise ValueError(f"LINEAR_BARCODE_CONFIG expects at least 3 arguments, but only found {args_count}!")
                    if args_count > 3:
                        raise ValueError(f"LINEAR_BARCODE_CONFIG expects at most 3 arguments, but found {args_count}!")
                    fld_bc_config = ZPL_Linear_Barcode_Config()
                    for i, arg in enumerate(args.split(",")):
                        if i == 0:
                            if not is_numeric(arg):
                                raise ValueError(f"LINEAR_BARCODE_CONFIG width must be a number. Could not convert {arg} into a number!")
                            fld_bc_config.module_width = int(arg)
                        elif i == 1:
                            if not is_numeric(arg):
                                raise ValueError(f"LINEAR_BARCODE_CONFIG bar width ratio must be a number. Could not convert {arg} into a number!")
                            fld_bc_config.bar_width_ratio = float(arg)
                        elif i == 2:
                            if not is_numeric(arg):
                                raise ValueError(f"LINEAR_BARCODE_CONFIG height must be a number. Could not convert {arg} into a number!")
                            fld_bc_config.module_height = int(arg)
                    
    
            if fld_type is None:
                raise ValueError("TYPE not set in field block!")
            elif fld_type == ZPL_Field_Type.TEXT:
                if fld_pos is None:
                    raise ValueError("POSITION not set in text field block!")
                if fld_font is None:
                    raise ValueError("FONT not set in text field block!")
                if fld_text is None:
                    raise ValueError("TEXT not set in text field block!")
                section.fields.append(ZPL_Text_Field(fld_label, fld_pos, fld_font, fld_text))
            elif fld_type == ZPL_Field_Type.BARCODE:
                ...
                # if fld_pos is None:
                #     raise ValueError("POSITION not set in barcode field block!")
                # if fld_bc_config is None:
                #     raise ValueError("LINEAR_BARCODE_CONFIG not set in barcode field block!")
                # if fld_bc_t
                # if fld_text is None:
                #     raise ValueError("TEXT not set in barcode field block!")
                # section.fields.append(ZPL_Linear_Barcode_Code39)


    doc.sections.append(section)
    return (doc, lines)

if __name__ == "__main__":
    fp = Path("./test.zplp")
    lines = get_file_data(fp)
    doc: ZPL_Document | None = None
    while len(lines) > 0:
        line = lines.pop(0)
        if line.startswith("//"):
            continue
        if line.startswith("DEF"):
            handle_def(line)
        elif line.startswith("BEGIN_DOCUMENT"):
            doc = ZPL_Document()
        elif line.startswith("BEGIN_SETUP"):
            if doc is not None:
                doc, lines = handle_setup(doc, line, lines)
        elif line.startswith("BEGIN_SECTION"):
            if doc is not None:
                doc, lines = handle_section(doc, line, lines)
        else:
            ...
    print(DEFINES)
    print(doc)