#define wmain native_bootstrap_main
#include "../../src/uu_native_wine_bootstrap.c"
#undef wmain

int wmain(int argc, WCHAR **argv)
{
    if (argc != 3) return 2;
    WCHAR identifier[256];
    DWORD audio_status = audio_settings(identifier, ARRAYSIZE(identifier));
    event("native_audio_endpoint", audio_status);
    if (audio_status || count != 2 || preflight() || apply_settings())
        return 1;
    WCHAR command[32768];
    int length = swprintf(command, ARRAYSIZE(command), L"\"%ls\" \"%ls\" 6", argv[1], argv[2]);
    if (length < 0 || (unsigned)length >= ARRAYSIZE(command)) return 1;
    STARTUPINFOW startup = {.cb = sizeof(startup)};
    PROCESS_INFORMATION child = {0};
    DWORD status = 1;
    if (CreateProcessW(argv[1], command, NULL, NULL, FALSE, 0, NULL, NULL, &startup, &child)) {
        if (WaitForSingleObject(child.hProcess, 15000) == WAIT_OBJECT_0)
            GetExitCodeProcess(child.hProcess, &status);
        else TerminateProcess(child.hProcess, 1);
        CloseHandle(child.hThread);
        CloseHandle(child.hProcess);
    }
    if (cleanup_settings()) return 1;
    if (preflight()) return 1;
    if (status) return 1;
    if (apply_settings()) return 1;
    HKEY key;
    const WCHAR *path = L"Software\\Wine\\Drivers\\winepulse.drv";
    if (RegOpenKeyExW(HKEY_CURRENT_USER, path, 0, KEY_QUERY_VALUE | KEY_SET_VALUE, &key)) return 1;
    const WCHAR changed[] = L"user-selected-audio-device";
    if (RegSetValueExW(key, L"DefaultOutput", 0, REG_SZ, (const BYTE *)changed, sizeof(changed))) return 1;
    if (cleanup_settings() != ERROR_INVALID_DATA) return 1;
    WCHAR buffer[256];
    DWORD bytes = sizeof(buffer);
    if (RegQueryValueExW(key, L"DefaultOutput", NULL, NULL, (BYTE *)buffer, &bytes) ||
        bytes != sizeof(changed) || wcscmp(buffer, changed)) return 1;
    if (RegDeleteValueW(key, L"DefaultOutput")) return 1;
    RegCloseKey(key);
    if (preflight()) return 1;
    puts("AUDIO real endpoint selection, WASAPI capture and owned registry cleanup passed");
    return 0;
}
