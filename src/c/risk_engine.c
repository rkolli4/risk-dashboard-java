#include <errno.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define BUFFER_SIZE 8192

typedef struct {
    double price;
    double total_deposit;
    double min_liquid_networth;
    double initial_margin;
    double extreme_loss_margin;
    double tm_limit;
    double position_qty;
    double position_limit;
    char captured_at[128];
} Snapshot;

static int read_number(const char *json, const char *key, double *value) {
    char needle[64];
    const char *match;
    snprintf(needle, sizeof(needle), "\"%s\"", key);
    match = strstr(json, needle);
    if (match == NULL) return 0;
    match = strchr(match, ':');
    if (match == NULL) return 0;
    return sscanf(match + 1, "%lf", value) == 1;
}

static int read_string(const char *json, const char *key, char *value, size_t capacity) {
    char needle[64];
    const char *match;
    snprintf(needle, sizeof(needle), "\"%s\"", key);
    match = strstr(json, needle);
    if (match == NULL) return 0;
    match = strchr(match, ':');
    if (match == NULL) return 0;
    match = strchr(match, '\"');
    if (match == NULL) return 0;
    match++;
    const char *end = strchr(match, '\"');
    if (end == NULL || (size_t)(end - match) >= capacity) return 0;
    memcpy(value, match, (size_t)(end - match));
    value[end - match] = '\0';
    return 1;
}

static int load_snapshot(const char *path, Snapshot *snapshot) {
    FILE *file = fopen(path, "rb");
    char buffer[BUFFER_SIZE];
    size_t length;
    if (file == NULL) { fprintf(stderr, "Cannot open %s: %s\n", path, strerror(errno)); return 0; }
    length = fread(buffer, 1, sizeof(buffer) - 1, file);
    fclose(file);
    buffer[length] = '\0';
    if (!read_number(buffer, "price", &snapshot->price) ||
        !read_number(buffer, "total_deposit", &snapshot->total_deposit) ||
        !read_number(buffer, "min_liquid_networth", &snapshot->min_liquid_networth) ||
        !read_number(buffer, "initial_margin", &snapshot->initial_margin) ||
        !read_number(buffer, "extreme_loss_margin", &snapshot->extreme_loss_margin) ||
        !read_number(buffer, "tm_limit", &snapshot->tm_limit) ||
        !read_number(buffer, "position_qty", &snapshot->position_qty) ||
        !read_number(buffer, "position_limit", &snapshot->position_limit) ||
        !read_string(buffer, "captured_at", snapshot->captured_at, sizeof(snapshot->captured_at))) {
        fprintf(stderr, "Snapshot is missing a required field\n");
        return 0;
    }
    return 1;
}

int main(int argc, char **argv) {
    const char *snapshot_path = argc > 1 ? argv[1] : "data/market_snapshot.json";
    const char *output_path = argc > 2 ? argv[2] : "data/risk_result.json";
    Snapshot snapshot;
    FILE *output;
    double exposure, utilization, penalty, liquid_networth;
    const char *state = "NORMAL";
    const char *message = "Exposure is within configured limits";

    if (!load_snapshot(snapshot_path, &snapshot)) return 1;
    exposure = fabs(snapshot.position_qty * snapshot.price);
    utilization = snapshot.position_limit > 0 ? exposure / snapshot.position_limit : 1.0;
    liquid_networth = snapshot.total_deposit - exposure;
    penalty = fmax(0.0, exposure - snapshot.tm_limit) * 0.02;

    if (liquid_networth < snapshot.min_liquid_networth || exposure >= snapshot.extreme_loss_margin * 20.0) {
        state = "DISABLED";
        message = "Trading disabled: liquid net worth or loss threshold breached";
    } else if (exposure > snapshot.initial_margin || utilization >= 0.8) {
        state = "PENALTY";
        message = "Penalty applied: margin or utilization threshold breached";
    } else if (exposure > snapshot.tm_limit) {
        state = "WARNING";
        message = "Warning: exposure exceeds the trading member limit";
    }

    output = fopen(output_path, "wb");
    if (output == NULL) { fprintf(stderr, "Cannot write %s: %s\n", output_path, strerror(errno)); return 1; }
    fprintf(output, "{\n  \"captured_at\": \"%s\",\n  \"state\": \"%s\",\n  \"exposure\": %.2f,\n  \"utilization\": %.6f,\n  \"penalty\": %.2f,\n  \"liquid_networth\": %.2f,\n  \"message\": \"%s\"\n}\n", snapshot.captured_at, state, exposure, utilization, penalty, liquid_networth, message);
    fclose(output);
    printf("Risk result: %s (exposure %.2f, utilization %.2f%%)\n", state, exposure, utilization * 100.0);
    return 0;
}
