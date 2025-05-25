import http.server
import socketserver
import json
import math
from src.core.parameters import Parameters # For type hint if needed
from src.core.state import State # For type hint if needed
from src.cli import get_parameters, get_initial_state, perform_dp_calculation, perform_simulation

PORT = 8080
MCP_PATH = "/mcp"

class MCPServerHandler(http.server.SimpleHTTPRequestHandler):
    
    def _send_json_response(self, status_code: int, data: dict):
        self.send_response(status_code)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_POST(self):
        if self.path != MCP_PATH:
            self.send_error(404, "Not Found")
            return

        try:
            content_length = int(self.headers['Content-Length'])
            post_data_bytes = self.rfile.read(content_length)
            post_data_str = post_data_bytes.decode('utf-8')
            payload = json.loads(post_data_str)
        except (TypeError, ValueError, json.JSONDecodeError, UnicodeDecodeError) as e:
            message = "Invalid request: "
            if isinstance(e, json.JSONDecodeError): message = "Invalid JSON format."
            elif isinstance(e, UnicodeDecodeError): message = "Invalid request encoding. Expected UTF-8."
            elif isinstance(e, (TypeError, ValueError)): message = f"Content-Length header issue: {e}"
            self._send_json_response(400, {"status": "error", "message": message})
            return

        command = payload.get("command")
        if not command:
            self._send_json_response(400, {"status": "error", "message": "Missing 'command' field in request."})
            return
        
        if command not in ["dp", "sim"]:
            self._send_json_response(400, {"status": "error", "message": f"Invalid command '{command}'. Must be 'dp' or 'sim'."})
            return

        try:
            # Parameter extraction and defaults
            n_matches = payload.get("n")
            if n_matches is None: # n is required for both dp and sim
                 self._send_json_response(400, {"status": "error", "message": "Missing required parameter 'n' (number of matches)."})
                 return
            if not isinstance(n_matches, int) or n_matches < 0:
                 self._send_json_response(400, {"status": "error", "message": "'n' must be a non-negative integer."})
                 return

            num_accounts = payload.get("accounts", 2) # Default from cli.py
            if not isinstance(num_accounts, int) or num_accounts <=0:
                self._send_json_response(400, {"status": "error", "message": "'accounts' must be a positive integer."})
                return

            initial_ratings_float = payload.get("initial") # Default is None
            if initial_ratings_float is not None:
                if not isinstance(initial_ratings_float, list) or not all(isinstance(r, (int, float)) for r in initial_ratings_float):
                    self._send_json_response(400, {"status": "error", "message": "'initial' must be a list of numbers."})
                    return
            
            param_data = {
                "rating_step": payload.get("rating_step", 16),
                "k_coeff": payload.get("k_coeff", math.log(10) / 1600),
                "mu": payload.get("mu", 1500.0)
            }
            # Type check for core params
            for p_name, p_val in param_data.items():
                 if not isinstance(p_val, (int, float)):
                    self._send_json_response(400, {"status": "error", "message": f"Parameter '{p_name}' must be a number."})
                    return


            core_params = get_parameters(param_data)
            initial_state = get_initial_state(num_accounts, initial_ratings_float, core_params)

            if command == "dp":
                results = perform_dp_calculation(n_matches, initial_state, core_params, num_accounts)
                # Structure: {'expected_value_int': ..., 'best_action_account_index': ..., ...}
                self._send_json_response(200, {"status": "success", "command": "dp", "results": results})
            
            elif command == "sim":
                episodes = payload.get("episodes", 1000)
                policy_name = payload.get("policy", "all")
                fixed_idx = payload.get("fixed_idx", 0)
                visualize = payload.get("visualize", False) # Default to False for server
                output_dir = payload.get("output_dir", ".") # Server might want to control this

                # Type checks for sim-specific params
                if not isinstance(episodes, int) or episodes <=0:
                    self._send_json_response(400, {"status": "error", "message": "'episodes' must be a positive integer."})
                    return
                if not isinstance(policy_name, str):
                     self._send_json_response(400, {"status": "error", "message": "'policy' must be a string."})
                     return
                if not isinstance(fixed_idx, int) or fixed_idx < 0:
                     self._send_json_response(400, {"status": "error", "message": "'fixed_idx' must be a non-negative integer."})
                     return
                if not isinstance(visualize, bool):
                     self._send_json_response(400, {"status": "error", "message": "'visualize' must be a boolean."})
                     return
                if not isinstance(output_dir, str):
                     self._send_json_response(400, {"status": "error", "message": "'output_dir' must be a string."})
                     return

                results = perform_simulation(
                    n_matches, initial_state, core_params, num_accounts,
                    episodes, policy_name, fixed_idx, visualize, output_dir
                )
                # Structure: {'simulation_results': ..., 'visualization_files': ..., 'error': ... (optional)}
                response_data = {"status": "success", "command": "sim", "results": results}
                if 'error' in results and results['error']: # Pass through visualization errors
                    response_data["warning_visualization"] = results['error']
                self._send_json_response(200, response_data)

        except ValueError as e: # Errors from get_initial_state, policy validation in perform_simulation etc.
            self._send_json_response(400, {"status": "error", "message": f"Parameter validation error: {e}"})
        except ImportError as e: # Specifically for matplotlib if visualize=True and not installed
            self._send_json_response(500, {"status": "error", "message": f"Server configuration error: Missing dependency for visualization. {e}"})
        except Exception as e:
            # Catch-all for other unexpected errors from core logic or elsewhere
            print(f"Unexpected server error: {e}") # Log to server console
            self._send_json_response(500, {"status": "error", "message": f"An unexpected server error occurred."})


    def do_GET(self):
        if self.path == MCP_PATH:
            self._send_json_response(405, {"status": "error", "message": "Method Not Allowed. Use POST."})
        else:
            # Fallback to SimpleHTTPRequestHandler's default GET handling (e.g. for serving files if needed)
            # If no file serving is intended, this could also be a 404.
            super().do_GET() 

def run_server(port=PORT):
    with socketserver.TCPServer(("", port), MCPServerHandler) as httpd:
        print(f"Serving at port {port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
            httpd.shutdown()

if __name__ == "__main__":
    run_server()
