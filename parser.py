from utils import *
from lexer import lex_file

if __name__ == "__main__":
    fp = Path("./test.zplp")
    lex = lex_file(fp)
    doc = ZPL_Document()
    for line in lex.lines:
        match line:
            case Def_Line():
                doc.parse_def_line(line)
            case Block_Begin_Line(): 
                match line.block_type:
                    case Block_Type.DOCUMENT:
                        doc.parse_begin_document_line(line)
                    case _:
                        ...
            case _:
                ...
    for d in doc.defines:
        print(f"{d} -> {doc.defines[d]}")