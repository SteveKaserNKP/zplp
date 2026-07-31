from zplp import *

if __name__ == "__main__":
    zplp = ZPLP_File("./test.zplp", "./commands.json")
    testing = False
    zpl = zplp.generate_zpl(testing)
    print(zpl)
    if testing:
        zplp.get_png(zpl)
    zplp.dump_zplp()
    zplp.save_to_file('./test.zpl', zpl)
