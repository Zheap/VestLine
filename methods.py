import glob
import subprocess

def add_source_files(self, sources, files):
    if isinstance(files, (str, bytes)):
        if files.startswith("#"):
            if "*" in files:
                print("ERROR: Wildcards can't be expanded in SCons project-absolute path: '{}'".format(files))
                return
            files = [files]
        else:
            skip_gen_cpp = "*" in files
            dir_path = self.Dir(".").abspath
            files = sorted(glob.glob(dir_path + "/" + files))
            if skip_gen_cpp:
                files = [f for f in files if not f.endswith(".gen.cpp")]

    for path in files:
        obj = self.Object(path)
        if obj in sources:
            print('WARNING: Object "{}" already included in environment sources.'.format(obj))
            continue
        sources.append(obj)

def disable_warnings(self):
    if self.msvc:
        self["CCFLAGS"] = [x for x in self["CCFLAGS"] if not (x.startswith("/W") or x.startswith("/w"))]
        self["CFLAGS"] = [x for x in self["CFLAGS"] if not (x.startswith("/W") or x.startswith("/w"))]
        self["CXXFLAGS"] = [x for x in self["CXXFLAGS"] if not (x.startswith("/W") or x.startswith("/w"))]
        self.AppendUnique(CCFLAGS=["/w"])
    else:
        self.AppendUnique(CCFLAGS=["-w"])

def add_shared_library(env, name, sources, **args):
    library = env.SharedLibrary(name, sources, **args)
    env.NoCache(library)
    return library

def add_library(env, name, sources, **args):
    library = env.Library(name, sources, **args)
    env.NoCache(library)
    return library

def add_program(env, name, sources, **args):
    program = env.Program(name, sources, **args)
    env.NoCache(program)
    return program



