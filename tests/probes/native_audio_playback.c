#include <pulse/pulseaudio.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

static void advance(pa_mainloop *loop)
{
    if (pa_mainloop_iterate(loop, 1, NULL) < 0) exit(1);
}

int main(int argc, char **argv)
{
    if (argc != 2) return 2;
    pa_mainloop *loop = pa_mainloop_new();
    if (!loop) return 1;
    pa_context *context = pa_context_new(pa_mainloop_get_api(loop), "uuway-audio-test");
    if (!context || pa_context_connect(context, NULL, PA_CONTEXT_NOFLAGS, NULL) < 0) return 1;
    while (pa_context_get_state(context) != PA_CONTEXT_READY) {
        if (!PA_CONTEXT_IS_GOOD(pa_context_get_state(context))) return 1;
        advance(loop);
    }
    pa_sample_spec specification = {.format = PA_SAMPLE_S16LE, .rate = 48000, .channels = 2};
    pa_channel_map channels;
    pa_channel_map_init_stereo(&channels);
    pa_stream *stream = pa_stream_new(context, "UUWay stereo test signal", &specification, &channels);
    pa_buffer_attr buffer = {.maxlength = (uint32_t)-1, .tlength = 3840, .prebuf = (uint32_t)-1,
                             .minreq = (uint32_t)-1, .fragsize = (uint32_t)-1};
    if (!stream || pa_stream_connect_playback(stream, argv[1], &buffer,
            PA_STREAM_DONT_MOVE | PA_STREAM_ADJUST_LATENCY, NULL, NULL) < 0) return 1;
    while (pa_stream_get_state(stream) != PA_STREAM_READY) {
        if (!PA_STREAM_IS_GOOD(pa_stream_get_state(stream))) return 1;
        advance(loop);
    }
    unsigned frame = 0;
    while (frame < 12 * 48000) {
        if (!PA_STREAM_IS_GOOD(pa_stream_get_state(stream))) return 1;
        size_t writable = pa_stream_writable_size(stream);
        if (writable == (size_t)-1) return 1;
        unsigned count = writable / 4;
        if (count > 480) count = 480;
        if (count > 12 * 48000 - frame) count = 12 * 48000 - frame;
        if (!count) { advance(loop); continue; }
        int16_t samples[960];
        for (unsigned index = 0; index < count; ++index) {
            double position = 2 * 3.14159265358979323846 * (frame + index) / 48000.0;
            samples[2 * index] = (int16_t)(3276 * sin(440 * position));
            samples[2 * index + 1] = (int16_t)(3276 * sin(880 * position));
        }
        if (pa_stream_write(stream, samples, count * 4, NULL, 0, PA_SEEK_RELATIVE) < 0) return 1;
        frame += count;
        if (pa_mainloop_iterate(loop, 0, NULL) < 0) return 1;
    }
    pa_operation *drain = pa_stream_drain(stream, NULL, NULL);
    if (!drain) return 1;
    while (pa_operation_get_state(drain) == PA_OPERATION_RUNNING) advance(loop);
    pa_operation_unref(drain);
    pa_stream_disconnect(stream);
    pa_stream_unref(stream);
    pa_context_disconnect(context);
    pa_context_unref(context);
    pa_mainloop_free(loop);
    return 0;
}
