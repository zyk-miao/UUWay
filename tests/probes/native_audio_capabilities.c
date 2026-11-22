#define COBJMACROS
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <initguid.h>
#include <mmdeviceapi.h>
#include <stdio.h>

int wmain(int argc, WCHAR **argv)
{
    WCHAR path[32768];
    if (argc > 2) return 2;
    const WCHAR *source = argc == 2 ? argv[1] : L"%WINDIR%\\system32\\audioses.dll";
    DWORD count = ExpandEnvironmentStringsW(source, path, ARRAYSIZE(path));
    if (!count || count > ARRAYSIZE(path)) return 1;
    HMODULE sessions = LoadLibraryExW(path, NULL, LOAD_WITH_ALTERED_SEARCH_PATH);
    if (!sessions) {
        printf("audioses load failed: %lu\n", GetLastError());
        return 1;
    }
    HRESULT status = CoInitializeEx(NULL, COINIT_MULTITHREADED);
    if (FAILED(status)) return 1;
    IMMDeviceEnumerator *enumerator = NULL;
    status = CoCreateInstance(&CLSID_MMDeviceEnumerator, NULL, CLSCTX_ALL,
        &IID_IMMDeviceEnumerator, (void **)&enumerator);
    printf("Core Audio enumeration: 0x%08lx\n", (unsigned long)status);
    if (SUCCEEDED(status)) IMMDeviceEnumerator_Release(enumerator);
    CoUninitialize();
    FreeLibrary(sessions);
    return FAILED(status) ? 1 : 0;
}
