#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <time.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/evp.h>

#define LAUNCHER_HOST "127.0.0.1"
#define LAUNCHER_PORT "5000"
#define STORE_SERVICE_ID "store-service"
#define TRANSPORT_SERVICE_ID "transport-service"
#define MESSAGING_SERVICE_ID "messaging-service"

static char program_id[32] = "1";
static char current_run_id[64] = "";
static FILE *metrics_fp = NULL;

static double now_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec * 1000.0 + (double)ts.tv_nsec / 1000000.0;
}

static void ensure_metrics_file(void) {
    if (metrics_fp) return;
    const char *path = getenv("METRICS_FILE");
    if (!path) path = "/tmp/all_metrics.csv";
    metrics_fp = fopen(path, "a");
    if (metrics_fp && ftell(metrics_fp) == 0) {
        fprintf(metrics_fp, "ts,run_id,component,operation,metric,value_ms,program_id,service_id\n");
        fflush(metrics_fp);
    }
}

static void metric(const char *operation, const char *metric_name, double value_ms, const char *service_id) {
    ensure_metrics_file();
    if (metrics_fp) {
        fprintf(metrics_fp, "%ld,%s,integration_process,%s,%s,%.6f,%s,%s\n", time(NULL), current_run_id, operation, metric_name, value_ms, program_id, service_id ? service_id : "");
        fflush(metrics_fp);
    }
}

static SSL_CTX *initialize_ssl_context(void) {
    OpenSSL_add_all_algorithms();
    SSL_load_error_strings();
    const SSL_METHOD *method = TLS_client_method();
    SSL_CTX *ctx = SSL_CTX_new(method);
    if (!ctx) {
        ERR_print_errors_fp(stderr);
        return NULL;
    }
    return ctx;
}

static void cleanup_ssl(SSL *ssl, SSL_CTX *ctx) {
    if (ssl) { SSL_shutdown(ssl); SSL_free(ssl); }
    if (ctx) SSL_CTX_free(ctx);
}

static char *http_post_json(const char *host, const char *port, const char *endpoint, const char *json_body) {
    SSL_CTX *ctx = NULL; SSL *ssl = NULL; int server = -1; struct sockaddr_in addr;
    char request[16384]; char buffer[4096]; size_t total = 0; char *response = NULL;
    ctx = initialize_ssl_context(); if (!ctx) goto cleanup;
    server = socket(AF_INET, SOCK_STREAM, 0); if (server < 0) goto cleanup;
    memset(&addr, 0, sizeof(addr)); addr.sin_family = AF_INET; addr.sin_port = htons(atoi(port)); inet_pton(AF_INET, host, &addr.sin_addr);
    if (connect(server, (struct sockaddr *)&addr, sizeof(addr)) < 0) goto cleanup;
    ssl = SSL_new(ctx); SSL_set_fd(ssl, server); if (SSL_connect(ssl) <= 0) goto cleanup;
    snprintf(request, sizeof(request), "POST %s HTTP/1.1\r\nHost: %s\r\nContent-Type: application/json\r\nContent-Length: %zu\r\nConnection: close\r\n\r\n%s", endpoint, host, strlen(json_body), json_body);
    SSL_write(ssl, request, (int)strlen(request));
    while (1) {
        int n = SSL_read(ssl, buffer, sizeof(buffer));
        if (n <= 0) break;
        char *tmp = realloc(response, total + n + 1); if (!tmp) { free(response); response = NULL; break; }
        response = tmp; memcpy(response + total, buffer, n); total += n; response[total] = '\0';
    }
cleanup:
    if (server >= 0) close(server); cleanup_ssl(ssl, ctx); return response;
}

static char *extract_http_json_body(char *response) {
    if (!response) return NULL; char *body = strstr(response, "\r\n\r\n"); if (!body) return strdup(response); body += 4; return strdup(body);
}

static char *json_get_string(const char *json, const char *key) {
    char pattern[128]; snprintf(pattern, sizeof(pattern), "\"%s\":\"", key); const char *start = strstr(json, pattern);
    if (!start) return NULL; start += strlen(pattern); const char *end = strchr(start, '"'); if (!end) return NULL;
    size_t len = (size_t)(end - start); char *out = malloc(len + 1); if (!out) return NULL; memcpy(out, start, len); out[len] = '\0'; return out;
}

static char *base64_encode_str(const char *input) {
    size_t len = strlen(input); size_t out_len = 4 * ((len + 2) / 3); unsigned char *out = malloc(out_len + 1); if (!out) return NULL;
    EVP_EncodeBlock(out, (const unsigned char *)input, (int)len); out[out_len] = '\0'; return (char *)out;
}

static char *base64_decode_str(const char *input) {
    size_t len = strlen(input); unsigned char *out = malloc(len + 1); if (!out) return NULL; int out_len = EVP_DecodeBlock(out, (const unsigned char *)input, (int)len);
    if (out_len < 0) { free(out); return NULL; } while (len > 0 && input[len - 1] == '=') { out_len--; len--; } out[out_len] = '\0'; return (char *)out;
}

static const char *getServicePublicKey(const char *srv_id) { (void)srv_id; return "service-public-key"; }
static char *encrypt_dataset(const char *public_key, const char *data) { (void)public_key; return base64_encode_str(data); }
static char *decrypt_dataset(const char *data_enc) { return base64_decode_str(data_enc); }

static char *build_run_id(void) {
    static unsigned counter = 0; counter++; snprintf(current_run_id, sizeof(current_run_id), "%ld-%u", time(NULL), counter); return current_run_id;
}

static char *read_action(const char *srv_id) {
    double t0 = now_ms();
    char endpoint[256]; char payload[256];
    snprintf(endpoint, sizeof(endpoint), "/api/read/%s/%s", srv_id, program_id);
    snprintf(payload, sizeof(payload), "{\"runId\":\"%s\"}", current_run_id);
    char *response = http_post_json(LAUNCHER_HOST, LAUNCHER_PORT, endpoint, payload);
    char *body = extract_http_json_body(response); free(response); if (!body) return NULL;
    char *data_enc = json_get_string(body, "dataEnc"); free(body);
    double td = now_ms(); char *plain = decrypt_dataset(data_enc ? data_enc : ""); metric("read", "decrypt_ms", now_ms() - td, srv_id); free(data_enc);
    metric("read", "read_act_total_ms", now_ms() - t0, srv_id); return plain;
}

static int write_action(const char *srv_id, const char *data) {
    double t0 = now_ms(); const char *puK = getServicePublicKey(srv_id);
    double te = now_ms(); char *data_enc = encrypt_dataset(puK, data); metric("write", "encrypt_ms", now_ms() - te, srv_id); if (!data_enc) return -1;
    char payload[8192]; char endpoint[256];
    snprintf(payload, sizeof(payload), "{\"dataEnc\":\"%s\",\"runId\":\"%s\"}", data_enc, current_run_id);
    snprintf(endpoint, sizeof(endpoint), "/api/write/%s/%s", srv_id, program_id);
    char *response = http_post_json(LAUNCHER_HOST, LAUNCHER_PORT, endpoint, payload); free(response); free(data_enc);
    metric("write", "write_act_total_ms", now_ms() - t0, srv_id); return 0;
}

static double extract_total_value(const char *data) { const char *p = strstr(data, "\"Total\":"); if (!p) return -1.0; p += strlen("\"Total\":"); return atof(p); }

static char *extract_json_string(const char *data, const char *key) {
    char pattern[64]; snprintf(pattern, sizeof(pattern), "\"%s\":\"", key); const char *start = strstr(data, pattern); if (!start) return NULL;
    start += strlen(pattern); const char *end = strchr(start, '"'); if (!end) return NULL; size_t len = (size_t)(end - start); char *out = malloc(len + 1); if (!out) return NULL; memcpy(out, start, len); out[len] = '\0'; return out;
}

static void process_business_flow(void) {
    build_run_id();
    char *sale_json = read_action(STORE_SERVICE_ID); if (!sale_json) { fprintf(stderr, "Failed to read sale data\n"); return; }
    double total = extract_total_value(sale_json);
    if (total > 150.0) {
        char *address = extract_json_string(sale_json, "Endereco"); char *phone = extract_json_string(sale_json, "Telefone");
        if (address && phone) {
            char payload1[2048]; snprintf(payload1, sizeof(payload1), "{\"local_origem\":\"Acme Store\",\"local_destino\":\"%s\",\"telefone_cliente\":\"%s\",\"valor\":%.2f}", address, phone, total);
            write_action(TRANSPORT_SERVICE_ID, payload1);
            char payload2[2048]; snprintf(payload2, sizeof(payload2), "{\"numero_telefone\":\"%s\",\"mensagem\":\"Your trip has been successfully booked. Wait for the car to arrive...!\"}", phone);
            write_action(MESSAGING_SERVICE_ID, payload2);
        }
        free(address); free(phone);
    }
    free(sale_json);
}

int main(void) {
    const char *pid_env = getenv("PROGRAM_ID"); if (pid_env && *pid_env) { strncpy(program_id, pid_env, sizeof(program_id)-1); program_id[sizeof(program_id)-1] = '\0'; }
    int max_loops = 1; const char *loops_env = getenv("MAX_LOOPS"); if (loops_env && *loops_env) max_loops = atoi(loops_env); if (max_loops <= 0) max_loops = 1;
    for (int i = 0; i < max_loops; ++i) { double t0 = now_ms(); process_business_flow(); metric("execute", "execute_total_ms", now_ms() - t0, ""); }
    if (metrics_fp) fclose(metrics_fp); return 0;
}
