# from platform_methods import subprocess_main

# def make_app_icon(target, source, env):
#     src = source[0]
#     dst = target[0]

#     with open(src, "rb") as f:
#         buf = f.read()

#     with open(dst, "w") as g:
#         g.write("/* THIS FILE IS GENERATED DO NOT EDIT */\n")
#         g.write("#ifndef APP_ICON_H\n")
#         g.write("#define APP_ICON_H\n")
#         g.write("static const unsigned char app_icon_png[] = {\n")
#         for i in range(len(buf)):
#             g.write(str[buf[i]] + ",\n")
#         g.write("};\n")
#         g.write("#endif")

# if __name__ == "__main__":
#     subprocess_main(globals())