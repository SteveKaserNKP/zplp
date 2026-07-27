from zplp import *

if __name__ == "__main__":
    zplp = ZPLP_File("./test.zplp", "./commands.json")
    zpl = zplp.generate_zpl(True)
    print(zpl)
    zplp.get_png(zpl)
    # for d in zplp.defines:
    #     print(f"{d} -> {zplp.defines[d]}")

    # print()

    # if zplp.document is not None and zplp.document.sections is not None:
    #     for s in zplp.document.sections:
    #         print(f"{s.label}")
    #         if s.fields is not None:
    #             for f in s.fields:
    #                 print(f"\t{f.label}")
    #                 for c in f.commands:
    #                     print(f"\t\t{c.schema.keyword}:")
    #                     for p in c.parameters:
    #                         if len(p.var_name) > 0:
    #                             print(f"\t\t\t{p.schema.name} => {p.var_name} = {p.value}")
    #                         else:
    #                             print(f"\t\t\t{p.schema.name} => {p.value}")
