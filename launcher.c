/*
 * Simple launcher for smbcmp windows build
 *
 * Copyright (C) 2019 Aurelien Aptel <aurelien.aptel@gmail.com>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#ifndef UNICODE
#define UNICODE
#endif

#include <shlwapi.h>
//compile with -Wl,-subsytem,windows -lshlwapi
//#pragma comment(lib, "shlwapi.lib")

LPWSTR get_process_dir(LPWSTR buf, size_t size)
{
	DWORD len = GetModuleFileName(NULL, buf, size);
	PathRemoveFileSpec(buf);
	return buf;
}

void show_error(void)
{
	LPVOID lpMsgBuf;
	DWORD dw = GetLastError();
	FormatMessageW(FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS,
		       NULL, dw, MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT), (LPWSTR)&lpMsgBuf, 0, NULL);

	MessageBoxW(NULL, (LPCWSTR)lpMsgBuf, L"Error", MB_OK | MB_ICONERROR);
	LocalFree(lpMsgBuf);
}

int run(void)
{
	WCHAR cmdline[MAX_PATH+1] = {0};
	WCHAR dir[MAX_PATH+1] = {0};
	WCHAR pypath[MAX_PATH+1] = {0};
	PROCESS_INFORMATION processInformation = {0};
	STARTUPINFO startupInfo = {0};
	startupInfo.cb = sizeof(startupInfo);

	// set current dir to the exe dir
	get_process_dir(dir, MAX_PATH);

	// set cmdline to call to "<py exe> <script>"
	wcscpy_s(cmdline, MAX_PATH, dir);
	wcscat_s(cmdline, MAX_PATH, L"\\python\\python.exe");
	wcscat_s(cmdline, MAX_PATH, L" smbcmp\\scripts\\smbcmp-gui -c .\\conf.ini");

	// set PYTHONPATH env var to "<current dir>\smbcmp"
	wcscpy_s(pypath, MAX_PATH, dir);
	wcscat_s(pypath, MAX_PATH, L"\\smbcmp");
	SetEnvironmentVariableW(L"PYTHONPATH", pypath);

	BOOL result = CreateProcessW(
		NULL, // exe name
		cmdline, // exe + args
		NULL, NULL, // proc and thread sec attributes
		FALSE, // inherit handles
		NORMAL_PRIORITY_CLASS | CREATE_NO_WINDOW, // creation flags
		NULL, // inherit env vars
		dir, // current dir
		&startupInfo,
		&processInformation);
	if (!result) {
		show_error();
		return 1;
	}

	WaitForSingleObject(processInformation.hProcess, INFINITE);
	CloseHandle(processInformation.hProcess);
	CloseHandle(processInformation.hThread);

	return 0;
}

int APIENTRY WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nShowCmd)
{
	return run();
}
