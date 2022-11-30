import os
import glob
import subprocess

from typing import Iterator

def add_source_files(self, sources, files):
    if isinstance(files, (str, bytes)):
        if files.startswith("#"):
            if "*" in files:
                print("ERROR: Wildcards can't be expanded in SCons project-absolute path: '{}'".format(files))
                return
            files = [files]
        else:
            skip_gen_cpp = "*" in files
            dir_path = self.Dir(".").abspath # Current dir's absolute path
            files = sorted(glob.glob(dir_path + "/" + files)) # glob.glob做路径匹配使用，返回该路径下所有匹配目录
            if skip_gen_cpp:
                files = [f for f in files if not f.endswith(".gen.cpp")]

    for path in files:
        obj = self.Object(path) # env.Object：StaticObject builder method, windows(.obj), posix(.o)
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

def add_shared_library(env, name, sources, **args):    # sources refer to object (.o on a POSIX system, .obj on Windows) or C, C++, D, or Fortran source files.
    library = env.SharedLibrary(name, sources, **args) # Builds a shared library (.so on a POSIX system, .dll on Windows), given one or more object files or C, C++, D or Fortran source files
    env.NoCache(library)
    return library

def add_library(env, name, sources, **args):
    library = env.Library(name, sources, **args) # Build a static library (.a on a POSIX system, .lib on Windows)
    env.NoCache(library)                         # Specifies a list of files which should not be cached
    return library

def add_program(env, name, sources, **args):
    program = env.Program(name, sources, **args) # Builds an executable given one or more object files or C, C++, D, or Fortran source files.
    env.NoCache(program)     
    return program

def find_visual_c_batch_file(env):
    from SCons.Tool.MSCommon.vc import (
        get_default_version,
        get_host_target,
        find_batch_file,
    )

    from SCons import __version__ as scons_raw_version

    scons_ver = env._get_major_minor_revision(scons_raw_version)
    
    version = get_default_version(env)

    if scons_ver >= (4, 4, 0):
        (host_platform, target_platform, _) = get_host_target(env, version)
    else:
        (host_platform, target_platform, _) = get_host_target(env)

    return find_batch_file(env, version, host_platform, target_platform)[0]

def glob_recursive(pattern, node="."):
    from SCons import Node
    from SCons.Script import Glob

    results = []
    for f in Glob(str(node) + "/*", source=True):
        if type(f) is Node.FS.Dir:
            results += glob_recursive(pattern, f)
    results += Glob(str(node) + "/" + pattern, source=True)
    return results

def add_to_vs_project(env, sources):
    for x in sources:
        if type(x) == type(""):
            fname = env.File(x).path  # File returns File Node(s)
        else:
            fname = env.File(x)[0].path
    pieces = fname.split(".")
    if len(pieces) > 0:
        basename = pieces[0]
        basename = basename.replace("\\\\", "/")
        if os.path.isfile(basename + ".h"):
            env.vs_incs += [basename + ".h"]
        elif os.path.isfile(basename + ".hpp"):
            env.vs_incs += [basename + ".hpp"]
        if os.path.isfile(basename + ".c"):
            env.vs_srcs += [basename + ".c"]
        elif os.path.isfile(basename + ".cpp"):
            env.vs_srcs += [basename + ".cpp"]

def generate_vs_project(env, num_jobs):
    batch_file = find_visual_c_batch_file(env)
    if batch_file:

        class ModuleConfigs(Mapping):
            PLATFORMS = ["Win32", "x64"]
            PLATFORM_IDS = ["x86_x32", "x86_x64"]
            CONFIGURATIONS = ["editor", "template_release", "template_debug"]
            DEV_SUFFIX = ".dev" if env["dev_build"] else ""

            @staticmethod
            def for_every_variant(value):
                return [value for _ in range(len(ModuleConfigs.CONFIGURATIONS) * len(ModuleConfigs.PLATFORMS))]
            
            def __init__(self):
                shared_targets_array = []
                self.names = []
                self.arg_dict = {
                    "variant": [],
                    "runfile": shared_targets_array,
                    "buildtarget": shared_targets_array,
                    "cpppaths": [],
                    "cppdefines": [],
                    "cmdargs": [],
                }
                self.add_mode()

            def add_mode(
                self,
                name: str = "",
                includes: str = "",
                cli_args: str = "",
                defines = None
            ):
                if defines in None:
                    defines = []
                self.names.append(name)
                self.arg_dict["variant"] += [
                    f'{config}{f"_[{name}]" if name else ""}|{platform}'
                    for config in ModuleConfigs.CONFIGURATIONS
                    for platform in ModuleConfigs.PLATFORMS
                ]
                self.arg_dict["runfile"] += [
                    f'bin\\godot.windows.{config}{ModuleConfigs.DEV_SUFFIX}{".double" if env["float"] == "64" else ""}.{plat_id}{f".{name}" if name else ""}.exe'
                    for config in ModuleConfigs.CONFIGURATIONS
                    for plat_id in ModuleConfigs.PLATFORM_IDS
                ]

                self.arg_dict["cpppaths"] += ModuleConfigs.for_every_variant(env["CPPPATH"] + [includes])
                self.arg_dict["cppdefines"] += ModuleConfigs.for_every_variant(env["CPPDEFINES"] + defines)
                self.arg_dict["cmdargs"] += ModuleConfigs.for_every_variant(cli_args)

            def build_commandline(self, commands):
                configuration_getter = (
                    "$(Configuration"
                    + "".join([f'.Replace("{name}", "")' for name in self.names[1:]])
                    + '.Replace("_[]","")'
                    + ")"
                )

                common_build_prefix = [
                    'cmd /V /C set "plat=$(PlatformTarget)"',
                    '(if "$(PlatformTarget)"=="x64" (set "plat=x86_amd64"))',
                    'call "' + batch_file + '" !plat!',
                ]

                common_build_postfix = [
                    "--directory=\"$(ProjectDir.TrimEnd('\\'))\"",
                    "platform=windows",
                    f"target={configuration_getter}",
                    "progress=no",
                    "-j%s" % num_jobs,
                ]

                if env["dev_build"]:
                    common_build_postfix.append("dev_build=yes")
                
                if env["dev_mode"]:
                    common_build_postfix.append("dev_mode=yes")
                
                elif env["tests"]:
                    common_build_postfix.append("tests=yes")
                
                if env["custom_modules"]:
                    common_build_postfix.append("custom_modules=%s" % env["custom_modules"])
                
                if env["float"] == "64":
                    common_build_postfix.append("float=64")
                
                result = " ^& ".join(common_build_prefix + [" ".join([commands] + common_build_postfix)])
                return result

            def __iter__(self) -> Iterator[str]:
                for x in self.arg_dict:
                    yield x
            
            def __len__(self) -> int:
                return len(self.names)
            
            def __getitem__(self, k: str):
                return self.arg_dict[k]
            
        add_to_vs_project(env, env.main_sources)

        for header in glob_recursive("**/*.h"):
            env.vs_incs.append(str(header))

        module_configs = ModuleConfigs()

        env["MSVSBUILDCOM"] = module_configs.build_commandline("scons")
        env["MSVSREBUILDCOM"] = module_configs.build_commandline("scons vsproj=yes")
        env["MSVSCLEANCOM"] = module_configs.build_commandline("scons --clean")

        if not env.get("MSVS"):
            env["MSVS"]["PROJECTSUFFIX"] = ".vcxproj"
            env["MSVS"]["SOLUTIONSUFFIX"] = ".sln"
        env.MSVSProject(
            target=["#vestline" + env["MSVSPROJECTSUFFIX"]],
            incs = env.vs_invs,
            srcs = env.vs_srcs,
            auto_build_solution = 1,
            **module_configs,
        )
    else:
        print("Could not locate Visual Studio batch file to set up the build environment. Not generating VS project.")
        