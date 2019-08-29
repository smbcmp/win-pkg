
Windows build packager for smbcmp
=================================

## Requirements

* Install wine, 7zip, unzip, mingw32-w64
* Get Wireshark Windows 64bit installer exe from https://wireshark.org
* Get Python **3.6** embedded 64bit Windows build from https://www.python.org/downloads/

## Usage

Run:

     ./make-release.py Wireshark-win64-3.0.3.exe  python-3.6.6-embed-amd64.zip ~/prog/smbcmp-git smbcmp-test

Note that the script will download pip and some python packages on
each run and will thus require an online connection.

If all goes well it should produce a directory `smbcmp-test` ready to
be zipped and uploaded.
