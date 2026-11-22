#define COBJMACROS
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <initguid.h>
#include <mmdeviceapi.h>
#include <audioclient.h>
#include <functiondiscoverykeys_devpkey.h>
#include <stdio.h>
#include <stdlib.h>
#include <wchar.h>
#include <ksmedia.h>

static void require(HRESULT result, const char *operation)
{
    if (FAILED(result)) {
        fprintf(stderr, "%s failed: 0x%08lx\n", operation, (unsigned long)result);
        exit(1);
    }
}

int wmain(int argc, WCHAR **argv)
{
    if (argc != 3) return 2;
    unsigned seconds = wcstoul(argv[2], NULL, 10);
    if (!seconds || seconds > 60) return 2;
    require(CoInitializeEx(NULL, COINIT_MULTITHREADED), "CoInitializeEx");
    IMMDeviceEnumerator *enumerator = NULL;
    IMMDevice *device = NULL;
    IAudioClient *client = NULL;
    IAudioCaptureClient *capture = NULL;
    require(CoCreateInstance(&CLSID_MMDeviceEnumerator, NULL, CLSCTX_ALL,
                            &IID_IMMDeviceEnumerator, (void **)&enumerator), "CoCreateInstance");
    require(IMMDeviceEnumerator_GetDefaultAudioEndpoint(enumerator, eRender, eConsole, &device),
            "GetDefaultAudioEndpoint");
    WCHAR expected[128];
    DWORD length = GetEnvironmentVariableW(L"UURB_AUDIO_SINK", expected, ARRAYSIZE(expected));
    if (length) {
        if (length >= ARRAYSIZE(expected)) return 1;
        IPropertyStore *properties = NULL;
        PROPVARIANT name;
        PropVariantInit(&name);
        require(IMMDevice_OpenPropertyStore(device, STGM_READ, &properties), "OpenPropertyStore");
        require(IPropertyStore_GetValue(properties, &PKEY_Device_FriendlyName, &name), "GetValue");
        if (name.vt != VT_LPWSTR || wcscmp(name.pwszVal, expected)) return 1;
        PropVariantClear(&name);
        IPropertyStore_Release(properties);
        puts("owned desktop audio endpoint selected");
    }
    require(IMMDevice_Activate(device, &IID_IAudioClient, CLSCTX_ALL, NULL, (void **)&client), "Activate");
    WAVEFORMATEX *format = NULL;
    require(IAudioClient_GetMixFormat(client, &format), "GetMixFormat");
    printf("mix tag=%u rate=%lu channels=%u bits=%u align=%u\n", format->wFormatTag,
           (unsigned long)format->nSamplesPerSec, format->nChannels, format->wBitsPerSample,
           format->nBlockAlign);
    WAVEFORMATEX pcm = {.wFormatTag = WAVE_FORMAT_PCM, .nChannels = 2, .nSamplesPerSec = 48000,
                       .nAvgBytesPerSec = 192000, .nBlockAlign = 4, .wBitsPerSample = 16};
    WAVEFORMATEX *closest = NULL;
    HRESULT supported = IAudioClient_IsFormatSupported(client, AUDCLNT_SHAREMODE_SHARED, &pcm, &closest);
    printf("48k stereo PCM16 format support=0x%08lx\n", (unsigned long)supported);
    CoTaskMemFree(closest);
    if (supported != S_OK) return 1;
    require(IAudioClient_Initialize(client, AUDCLNT_SHAREMODE_SHARED,
            AUDCLNT_STREAMFLAGS_LOOPBACK | AUDCLNT_STREAMFLAGS_EVENTCALLBACK |
            AUDCLNT_STREAMFLAGS_AUTOCONVERTPCM | AUDCLNT_STREAMFLAGS_SRC_DEFAULT_QUALITY,
            1000000, 0, &pcm, NULL), "Initialize loopback");
    HANDLE ready = CreateEventW(NULL, FALSE, FALSE, NULL);
    if (!ready) return 1;
    require(IAudioClient_SetEventHandle(client, ready), "SetEventHandle");
    require(IAudioClient_GetService(client, &IID_IAudioCaptureClient, (void **)&capture), "GetService");
    FILE *output = _wfopen(argv[1], L"wb");
    if (!output) return 1;
    require(IAudioClient_Start(client), "Start");
    ULONGLONG deadline = GetTickCount64() + seconds * 1000;
    unsigned long long total = 0;
    while (GetTickCount64() < deadline) {
        if (WaitForSingleObject(ready, 2000) != WAIT_OBJECT_0) return 1;
        UINT32 count;
        require(IAudioCaptureClient_GetNextPacketSize(capture, &count), "GetNextPacketSize");
        while (count) {
            BYTE *data;
            UINT32 frames;
            DWORD flags;
            require(IAudioCaptureClient_GetBuffer(capture, &data, &frames, &flags, NULL, NULL), "GetBuffer");
            if (flags & AUDCLNT_BUFFERFLAGS_SILENT) {
                const BYTE zero[4] = {0};
                for (UINT32 i = 0; i < frames; ++i)
                    if (fwrite(zero, 4, 1, output) != 1) return 1;
            } else if (fwrite(data, 4, frames, output) != frames) return 1;
            total += frames;
            require(IAudioCaptureClient_ReleaseBuffer(capture, frames), "ReleaseBuffer");
            require(IAudioCaptureClient_GetNextPacketSize(capture, &count), "GetNextPacketSize");
        }
    }
    require(IAudioClient_Stop(client), "Stop");
    if (fclose(output)) return 1;
    printf("captured_frames=%llu\n", total);
    IAudioCaptureClient_Release(capture);
    IAudioClient_Release(client);
    IMMDevice_Release(device);
    IMMDeviceEnumerator_Release(enumerator);
    CoTaskMemFree(format);
    CloseHandle(ready);
    CoUninitialize();
    return total >= seconds * 40000 ? 0 : 1;
}
