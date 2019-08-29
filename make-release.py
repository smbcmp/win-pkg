#!/usr/bin/env python3
import os
import subprocess
import errno
import argparse
import re

BIN = {}
DIR = os.path.dirname(os.path.realpath(__file__))

# ? at beginning means optional file
TSHARK_FILES = r'''
AUTHORS-SHORT
?(lib)?brotlicommon\.dll
?(lib)?brotlidec\.dll
(lib)?cares\.dll
cfilters
colorfilters
(lib)?comerr(32|64)\.dll
console\.lua
COPYING\.txt
dfilters
dtd_gen\.lua
enterprises\.tsv
(lib)?glib-.+\.dll
(lib)?gmodule-.+\.dll
?(lib)?gthread-.+\.dll
init\.lua
(lib)?k5sprt(32|64)\.dll
(lib)?krb5_(32|64)\.dll
(lib)?bcg\d+\.dll
?(lib)?charset\.dll
(lib)?ffi-.*\.dll
(lib)?gcc_s_.+\.dll
(lib)?gcrypt-.+\.dll
(lib)?gmp-.+\.dll
(lib)?gnutls-.+\.dll
(lib)?gpg-error-.*\.dll
(lib)?hogweed-.+\.dll
?(lib)?iconv\.dll
(lib)?intl.*\.dll
(lib)?maxminddb-.*\.dll
(lib)?nettle-.+\.dll
(lib)?nghttp2.*\.dll
(lib)?p11-kit-.*\.dll
(lib)?sbc-.+\.dll
(lib)?smi-.+\.dll
(lib)?snappy-.+\.dll
(lib)?spandsp-.+\.dll
(lib)?ssh\.dll
(lib)?tasn1-.+\.dll
(lib)?winpthread-.*\.dll
(lib)?wireshark\.dll
(lib)?wiretap\.dll
(lib)?wsutil\.dll
(lib)?xml2.*\.dll
(lib)?lua52\.dll
(lib)?lz4\.dll
?(lib)?lzma\.dll
manuf
?(lib)?pcre\.dll
?services
?smi_modules
tshark\.exe
?wka
(lib)?zlib1\.dll
'''

SMBCMP_FILES = '''
LICENSE
smbcmp/common.py
smbcmp/__init__.py
scripts/smbcmp
scripts/smbcmp-gui
README.md
'''

def main():
    ap = argparse.ArgumentParser(description="Package smbcmp for windows")
    ap.add_argument("wshark", help="path to a Wireshark installer (.exe)")
    ap.add_argument("python", help="path to a Windows embedded python release (.zip)")
    ap.add_argument("smbcmp", help="path to smbcmp git repo")
    ap.add_argument("out", help="path to output directory")
    args = ap.parse_args()

    check_all_bins()

    check_exists(args.out, False)
    check_exists(args.wshark)
    check_exists(args.python)
    check_exists(args.smbcmp)

    if args.wshark.lower().endswith(".msi"):
        msi = True
    elif args.wshark.lower().endswith(".exe"):
        msi = False
    else:
        err("require .exe or .msi wireshark installer")
    
    global SMBCMP_FILES
    global TSHARK_FILES

    SMBCMP_FILES = parse_file_list(SMBCMP_FILES)
    TSHARK_FILES = parse_file_list(TSHARK_FILES)

    try:
        info("extracting wireshark")
    
        try:
            tmpdir = os.path.join(DIR, "ws_tmp")
            run(['rm', '-rf', tmpdir])
            if msi:
                if not check_bin("msiextract", pkg="msitools"):
                    err("msiextract required")
                run(['msiextract', '-C', tmpdir, args.wshark])
                subdir = os.path.join(tmpdir, 'Program Files', 'Wireshark')            
            else:
                if not check_bin("7z", pkg="p7zip"):
                    err("7z required")
                run(['7z', 'x', '-aoa', '-o'+tmpdir, args.wshark])
                subdir = tmpdir
    
            mkdir_p(args.out)
            tsharkdir = os.path.join(args.out, 'tshark')
            mkdir_p(tsharkdir)
            dirlist = os.listdir(subdir)
            for rx in TSHARK_FILES:
                opt = False
                if rx[0] == '?':
                    opt = True
                    rx = rx[1:]
                fn = first_match(lambda fn: re.match(rx, fn), dirlist)
                if not fn:
                    if opt:
                        continue
                    else:
                        err("cannot find file %s"%rx)
                info("copying %s"%fn)
                full = os.path.join(subdir, fn)
                run(['cp', full, tsharkdir])
        finally:
            run(['rm', '-rf', tmpdir])

        info("extracting python")

        pydir = os.path.join(args.out, "python")
        mkdir_p(pydir)
        run(['unzip', '-d', pydir, args.python])
        pth = first_match(lambda x: re.match(r'python\d+\._pth', x), os.listdir(pydir))
        if pth is None:
            err("no python??._pth file")
        run(['rm', os.path.join(pydir, pth)])

        info("getting pip")
        pip = os.path.join(args.out, "get-pip.py")
        run(['wget', '-q', '-O', pip, 'https://bootstrap.pypa.io/get-pip.py'])

        info("installing pip")
        run(['wine', 'python/python.exe', 'get-pip.py'], cwd=args.out)
        run(['rm', pip])

        def pip_install(pkg):
            info("pip install %s"%pkg)
            run(['wine', 'Scripts/pip.exe', 'install', pkg], cwd=pydir)

        pip_install('windows-curses')
        pip_install('wxpython')

        info("installing smbcmp")

        smbdir = os.path.join(args.out, "smbcmp")
        mkdir_p(smbdir)
        for fn in SMBCMP_FILES:
            info("copying %s"%fn)
            full = os.path.join(args.smbcmp, fn)
            check_exists(full)

            dst = os.path.join(smbdir, fn)
            fpath, fname = os.path.split(dst)
            mkdir_p(fpath)
            run(['cp', full, dst])

        info("compiling launcher")

        run(['CC', os.path.join(DIR, 'launcher.c'),
             '-Wl,-subsystem,windows', '-lshlwapi',
             '-o', os.path.join(args.out, 'smbcmp.exe')])

        info("copying licenses...")
        run(['cp',
             os.path.join(DIR, 'LICENSE.txt'),
             os.path.join(DIR, 'LICENSE.python.txt'),
             os.path.join(DIR, 'LICENSE.wireshark.txt'),
             args.out,
        ])
        
        info("writing conf")
        with open(os.path.join(args.out, "conf.ini"), "w+") as f:
            print("[global]\ntshark_path = .\\tshark\\tshark.exe", file=f)

        info("all done!")

    except:
        warn("hit exception, clearing output dir")
        run(['rm', '-rf', args.out])
        raise

def first_match(pred, it):
    for i in it:
        if pred(i):
            return i
    return None

def run(cmd, **kwargs):
    if cmd[0].upper() in BIN:
        cmd[0] = BIN[cmd[0].upper()]
    subprocess.check_call(cmd, **kwargs)

def check_exists(path, exists=True, msg=None):
    r = os.path.exists(path)
    if not msg:
        if exists:
            msg = "%s doesn't exist"%path
        else:
            msg = "%s already exist"%path
    if (not r and exists) or (r and not exists):
        err(msg)

def check_all_bins():
    r = True
    r &= check_bin('wine')
    r &= check_bin('unzip')
    r &= check_bin('zip')
    r &= check_bin('wget')
    r &= check_bin('x86_64-w64-mingw32-gcc', name="CC", pkg='mingw64-gcc')
    if not r:
        print("missing dependencies, stopping")
        exit(1)

def which(program):
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None

def check_bin(prog, name=None, pkg=None):
    print("checking for %s"%prog)
    if name is None:
        name = prog.upper()
    env = os.environ.get(name, None)
    if env:
        print("using env var %s -> %s"%(name, env))
        prog = env
    r = which(prog)
    if r is None:
        print("cannot find prog %s"%prog)
        if not env:
            print("you can provide a path via the env var %s"%name)
        if pkg:
            print("try installing %s"%pkg)
        return False
    BIN[name] = prog
    return True

def parse_file_list(fns):
    return [x for x in fns.split("\n") if len(x) > 0]

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def info(s):
    print("[*]", s)

def warn(s):
    print("[W]", s)

def err(s):
    print("[E]", s)
    exit(1)

if __name__ == '__main__':
    main()
