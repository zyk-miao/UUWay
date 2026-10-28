#define UURB_NATIVE_INPUT_ONLY
#include "../../src/uu_input_bridge.c"

#define REQUIRE(value) do { if (!(value)) { \
    fprintf(stderr, "KDE live display check failed at line %d: %s\n", __LINE__, #value); \
    goto done; } } while (0)

static BOOL query_live(UINT32 *count, DISPLAYCONFIG_PATH_INFO *paths,
                       UINT32 *mode_count, DISPLAYCONFIG_MODE_INFO *modes)
{
    struct uurb_display_topology current;
    LONG result = ERROR_GEN_FAILURE;
    if (!native_multi_snapshot(&current, TRUE)) return FALSE;
    *count = 8;
    *mode_count = 24;
    return native_multi_query_config(QDC_ONLY_ACTIVE_PATHS, count, paths, mode_count, modes,
                                     NULL, &result) == 1 && result == ERROR_SUCCESS;
}

int wmain(int argc, WCHAR **argv)
{
    if (argc != 3) return 2;
    int status = 1;
    BOOL created_zero = FALSE, created_seven = FALSE;
    DWORD slot = 7, plug[6] = {7, 0, 0, 0, 0, 0};
    UINT32 physical_count, physical_mode_count;
    DISPLAYCONFIG_PATH_INFO physical[8];
    DISPLAYCONFIG_MODE_INFO physical_modes[24];
    SetEnvironmentVariableW(L"UURB_DISPLAY_SOCKET", argv[1]);
    SetEnvironmentVariableW(L"UURB_DISPLAY_ALLOW_CHANGES", L"1");
    REQUIRE(native_display_adapter_initialize() == 1);
    REQUIRE(query_live(&physical_count, physical, &physical_mode_count, physical_modes));
    struct uurb_display_topology snapshot;
    REQUIRE(native_multi_snapshot(&snapshot, TRUE));
    for (UINT i = 0; i < snapshot.monitor_count; ++i)
        REQUIRE(!(snapshot.monitors[i].flags & UURB_DISPLAY_MONITOR_VIRTUAL));
    REQUIRE(snapshot.monitors[0].flags & UURB_DISPLAY_MONITOR_KSCREEN);
    struct uurb_display_topology original = snapshot;

    DWORD initial_plug[6] = {0};
    REQUIRE(native_virtual_control_api(native_display_endpoint, 0x30c004, initial_plug, sizeof(initial_plug)) == 0);
    created_zero = TRUE;
    UINT32 initial_count, initial_mode_count;
    DISPLAYCONFIG_PATH_INFO initial_paths[8];
    DISPLAYCONFIG_MODE_INFO initial_modes[24];
    REQUIRE(query_live(&initial_count, initial_paths, &initial_mode_count, initial_modes));
    REQUIRE(native_display_set_config(initial_count, initial_paths, initial_mode_count, initial_modes, 0x16a0) == ERROR_SUCCESS);
    REQUIRE(native_multi_snapshot(&snapshot, TRUE));
    REQUIRE(snapshot.monitor_count == (wcstoul(argv[2], NULL, 10) ? 1 : physical_count));
    REQUIRE(native_display_set_config(physical_count, physical, physical_mode_count, physical_modes, 0x14a0) == ERROR_SUCCESS);
    REQUIRE(native_display_set_config(physical_count, physical, physical_mode_count, physical_modes, 0x10a0) == ERROR_SUCCESS);
    created_zero = FALSE;
    puts("KDE_LIVE_DISPLAY_OFF initial activation and repeated physical restore passed");

    const UINT32 restore_flags[] = {0x14a0, 0x10a0};
    for (UINT test = 0; test < ARRAYSIZE(restore_flags); ++test) {
        REQUIRE(native_virtual_control_api(native_display_endpoint, 0x30c004, plug, sizeof(plug)) == 0);
        created_seven = TRUE;
        UINT32 count, mode_count;
        DISPLAYCONFIG_PATH_INFO paths[8];
        DISPLAYCONFIG_MODE_INFO modes[24];
        REQUIRE(query_live(&count, paths, &mode_count, modes));
        REQUIRE(count == physical_count + 1);
        REQUIRE(native_multi_snapshot(&snapshot, TRUE));
        UINT virtual_index = UINT_MAX;
        for (UINT i = 0; i < snapshot.monitor_count; ++i)
            if (snapshot.monitors[i].flags & UURB_DISPLAY_MONITOR_VIRTUAL) virtual_index = i;
        REQUIRE(virtual_index < count);
        DISPLAYCONFIG_PATH_INFO selected = paths[virtual_index];
        DISPLAYCONFIG_MODE_INFO selected_modes[24];
        memcpy(selected_modes, modes, sizeof(modes));
        selected_modes[selected.sourceInfo.modeInfoIdx].sourceMode.position = (POINTL){0, 0};
        REQUIRE(native_display_set_config(1, &selected, mode_count, selected_modes, 0x16a0) == ERROR_SUCCESS);
        REQUIRE(native_multi_snapshot(&snapshot, TRUE));
        REQUIRE(snapshot.monitor_count == 1 && snapshot.monitors[0].flags & UURB_DISPLAY_MONITOR_VIRTUAL);

        REQUIRE(native_display_set_config(count, paths, mode_count, modes, 0x16a0) == ERROR_SUCCESS);
        REQUIRE(native_multi_snapshot(&snapshot, TRUE));
        REQUIRE(snapshot.monitor_count == physical_count + 1);
        REQUIRE(!(snapshot.monitors[0].flags & UURB_DISPLAY_MONITOR_VIRTUAL));

        REQUIRE(native_display_set_config(1, &selected, mode_count, selected_modes, 0x16a0) == ERROR_SUCCESS);
        REQUIRE(native_display_set_config(physical_count, physical, physical_mode_count, physical_modes,
                                          (restore_flags[test] & ~SDC_APPLY) | SDC_VALIDATE) == ERROR_SUCCESS);
        REQUIRE(native_multi_snapshot(&snapshot, TRUE));
        REQUIRE(snapshot.monitor_count == 1);
        REQUIRE(native_display_set_config(physical_count, physical, physical_mode_count, physical_modes,
                                          restore_flags[test]) == ERROR_SUCCESS);
        REQUIRE(native_multi_snapshot(&snapshot, TRUE));
        REQUIRE(snapshot.monitor_count == physical_count);
        created_seven = FALSE;
        for (UINT i = 0; i < snapshot.monitor_count; ++i) {
            REQUIRE(!(snapshot.monitors[i].flags & UURB_DISPLAY_MONITOR_VIRTUAL));
            REQUIRE(!strcmp(snapshot.monitors[i].gdi_name, original.monitors[i].gdi_name));
            REQUIRE(!strcmp(snapshot.monitors[i].device_path, original.monitors[i].device_path));
            REQUIRE(snapshot.monitors[i].x == original.monitors[i].x &&
                    snapshot.monitors[i].y == original.monitors[i].y);
        }
        printf("KDE_LIVE_RESTORE flags=%lu physical_outputs=%u passed\n",
               (unsigned long)restore_flags[test], snapshot.monitor_count);
    }
    status = 0;
done:
    if (native_virtual_control_api) {
        if (created_seven)
            native_virtual_control_api(native_display_endpoint, 0x30c008, &slot, sizeof(slot));
        slot = 0;
        if (created_zero)
            native_virtual_control_api(native_display_endpoint, 0x30c008, &slot, sizeof(slot));
    }
    return status;
}
