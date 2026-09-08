import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class RiskUiApp {
    private static final Path RESULT = Path.of("data", "risk_result.json");
    private static final Pattern VALUE = Pattern.compile("\\\"([^\\\"]+)\\\"\\s*:\\s*(?:\\\"([^\\\"]*)\\\"|([-0-9.]+))");

    private static String resultJson() throws IOException {
        return Files.exists(RESULT) ? Files.readString(RESULT) : "{\"state\":\"WAITING\",\"message\":\"Run the pipeline to create a risk result\"}";
    }

    private static String value(String json, String key, String fallback) {
        Matcher matcher = VALUE.matcher(json);
        while (matcher.find()) if (matcher.group(1).equals(key)) return matcher.group(2) != null ? matcher.group(2) : matcher.group(3);
        return fallback;
    }

    private static String page() throws IOException {
        String json = resultJson();
        String state = value(json, "state", "WAITING");
        return "<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>PRISM Risk Console</title>" +
                "<style>:root{font-family:Georgia,serif;color:#102a2c;background:#f4f0e8}body{margin:0;min-height:100vh;background:radial-gradient(circle at 80% 10%,#f7d6a3,transparent 32%),#f4f0e8}.wrap{max-width:960px;margin:auto;padding:48px 24px}.eyebrow{font:700 12px Arial;letter-spacing:2px;color:#b34b2d}.hero{display:flex;justify-content:space-between;align-items:end;gap:24px;border-bottom:2px solid #102a2c;padding-bottom:28px}.hero h1{font-size:clamp(42px,8vw,88px);line-height:.9;margin:10px 0 0}.timestamp{font:13px Arial;color:#536363}.state{margin:32px 0;padding:28px;background:#102a2c;color:#fff;display:flex;justify-content:space-between;align-items:center}.state strong{font-size:40px}.state span{font:16px Arial;color:#d5e5dd}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.metric{border-top:5px solid #b34b2d;padding:18px 0}.metric label{font:12px Arial;text-transform:uppercase;color:#536363}.metric b{display:block;font-size:32px;margin-top:8px}@media(max-width:640px){.hero{display:block}.state{display:block}.state span{display:block;margin-top:12px}.grid{grid-template-columns:1fr 1fr}}</style></head><body><main class='wrap'><div class='hero'><div><div class='eyebrow'>PRISM / MARKET CONTROLS</div><h1>Risk<br>Console</h1></div><div class='timestamp'>Snapshot: " + value(json, "captured_at", "not available") + "</div></div><section class='state'><strong>" + state + "</strong><span>" + value(json, "message", "No result yet") + "</span></section><section class='grid'><div class='metric'><label>Exposure</label><b>" + value(json, "exposure", "-") + "</b></div><div class='metric'><label>Utilization</label><b>" + value(json, "utilization", "-") + "</b></div><div class='metric'><label>Penalty</label><b>" + value(json, "penalty", "-") + "</b></div></section></main></body></html>";
    }

    private static void respond(HttpExchange exchange, int status, String contentType, String body) throws IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", contentType + "; charset=utf-8");
        exchange.sendResponseHeaders(status, bytes.length);
        try (OutputStream output = exchange.getResponseBody()) { output.write(bytes); }
    }

    public static void main(String[] args) throws IOException {
        int port = args.length > 0 ? Integer.parseInt(args[0]) : 8080;
        HttpServer server = HttpServer.create(new InetSocketAddress(port), 0);
        server.createContext("/api/risk", exchange -> respond(exchange, 200, "application/json", resultJson()));
        server.createContext("/", exchange -> respond(exchange, 200, "text/html", page()));
        server.start();
        System.out.println("PRISM UI running at http://localhost:" + port);
    }
}
