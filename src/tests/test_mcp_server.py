import unittest
from unittest.mock import patch, MagicMock, call
import json
import io
import math

# Assuming src.mcp_server and src.cli are importable
# Adjust path if necessary, e.g. by setting PYTHONPATH or using sys.path.append
from src.mcp_server import MCPServerHandler, MCP_PATH
from src.core.parameters import Parameters # For creating mock return values
from src.core.state import State # For creating mock return values

# Default parameters from cli.py to help construct expected calls
DEFAULT_RATING_STEP = 16
DEFAULT_K_COEFF = math.log(10) / 1600
DEFAULT_MU = 1500.0
DEFAULT_ACCOUNTS = 2
DEFAULT_EPISODES = 1000
DEFAULT_POLICY = "all"
DEFAULT_FIXED_IDX = 0
DEFAULT_VISUALIZE = False # Server default for visualize
DEFAULT_OUTPUT_DIR = "."


class TestMCPServerHandler(unittest.TestCase):

    def setUp(self):
        self.mock_rfile = MagicMock(spec=io.BytesIO)
        self.mock_wfile = MagicMock(spec=io.BytesIO)
        
        # Mock the base class methods used for sending responses
        self.mock_send_response = MagicMock()
        self.mock_send_header = MagicMock()
        self.mock_end_headers = MagicMock()

        # Create a partial instance of the handler or mock its base methods
        self.handler = MCPServerHandler(MagicMock(), MagicMock(), MagicMock()) # request, client_address, server
        self.handler.rfile = self.mock_rfile
        self.handler.wfile = self.mock_wfile
        self.handler.send_response = self.mock_send_response
        self.handler.send_header = self.mock_send_header
        self.handler.end_headers = self.mock_end_headers
        # _send_json_response is part of MCPServerHandler, so it will use the mocked send_response etc.

    def _simulate_post_request(self, path, data: dict = None, headers: dict = None, body_bytes: bytes = None):
        self.handler.path = path
        self.handler.headers = headers if headers else {}
        
        if body_bytes is not None:
            self.mock_rfile.read.return_value = body_bytes
            self.handler.headers['Content-Length'] = str(len(body_bytes))
        elif data is not None:
            body_str = json.dumps(data)
            body_bytes_encoded = body_str.encode('utf-8')
            self.mock_rfile.read.return_value = body_bytes_encoded
            self.handler.headers['Content-Length'] = str(len(body_bytes_encoded))
        else: # No body
             self.handler.headers['Content-Length'] = '0'
             self.mock_rfile.read.return_value = b''


        self.handler.do_POST()

    def _get_response_data(self):
        # Assumes _send_json_response was called, which internally calls self.wfile.write
        # and that self.wfile is a MagicMock
        if self.mock_wfile.write.call_args:
            return json.loads(self.mock_wfile.write.call_args[0][0].decode('utf-8'))
        return None

    # 1. Basic Server Functionality
    def test_invalid_path_post(self):
        self.handler.send_error = MagicMock() # Mock send_error for this test
        self._simulate_post_request("/invalid_path", {})
        self.handler.send_error.assert_called_once_with(404, "Not Found")

    def test_get_request_to_mcp_path(self):
        self.handler.path = MCP_PATH
        self.handler.do_GET() # Call do_GET directly
        self.mock_send_response.assert_called_once_with(405)
        response_data = self._get_response_data()
        self.assertEqual(response_data['status'], 'error')
        self.assertEqual(response_data['message'], "Method Not Allowed. Use POST.")

    # 2. Request Parsing and Validation
    def test_invalid_json_body(self):
        self._simulate_post_request(MCP_PATH, body_bytes=b"{'invalid_json':}")
        self.mock_send_response.assert_called_once_with(400)
        response_data = self._get_response_data()
        self.assertEqual(response_data['status'], 'error')
        self.assertIn("Invalid JSON format", response_data['message'])

    def test_non_utf8_encoding(self):
        # Simulate data that cannot be decoded as UTF-8
        self._simulate_post_request(MCP_PATH, body_bytes=b'\xff\xfeinvalid')
        self.mock_send_response.assert_called_once_with(400)
        response_data = self._get_response_data()
        self.assertEqual(response_data['status'], 'error')
        self.assertIn("Invalid request encoding. Expected UTF-8.", response_data['message'])

    def test_missing_command_field(self):
        self._simulate_post_request(MCP_PATH, data={"some_param": "value"})
        self.mock_send_response.assert_called_once_with(400)
        response_data = self._get_response_data()
        self.assertEqual(response_data['status'], 'error')
        self.assertEqual(response_data['message'], "Missing 'command' field in request.")

    def test_invalid_command_value(self):
        self._simulate_post_request(MCP_PATH, data={"command": "unknown_cmd", "n": 10})
        self.mock_send_response.assert_called_once_with(400)
        response_data = self._get_response_data()
        self.assertEqual(response_data['status'], 'error')
        self.assertIn("Invalid command 'unknown_cmd'", response_data['message'])

    def test_missing_n_parameter(self):
        self._simulate_post_request(MCP_PATH, data={"command": "dp"})
        self.mock_send_response.assert_called_once_with(400)
        response_data = self._get_response_data()
        self.assertEqual(response_data['status'], 'error')
        self.assertEqual(response_data['message'], "Missing required parameter 'n' (number of matches).")
    
    def test_invalid_type_for_n(self):
        self._simulate_post_request(MCP_PATH, data={"command": "dp", "n": "not_an_int"})
        self.mock_send_response.assert_called_once_with(400)
        response_data = self._get_response_data()
        self.assertEqual(response_data['status'], 'error')
        self.assertEqual(response_data['message'], "'n' must be a non-negative integer.")

    def test_invalid_type_for_accounts(self):
        self._simulate_post_request(MCP_PATH, data={"command": "dp", "n": 10, "accounts": "two"})
        self.mock_send_response.assert_called_once_with(400)
        response_data = self._get_response_data()
        self.assertEqual(response_data['status'], 'error')
        self.assertEqual(response_data['message'], "'accounts' must be a positive integer.")

    def test_invalid_type_for_initial(self):
        self._simulate_post_request(MCP_PATH, data={"command": "dp", "n": 10, "initial": "not_a_list"})
        self.mock_send_response.assert_called_once_with(400)
        response_data = self._get_response_data()
        self.assertEqual(response_data['status'], 'error')
        self.assertEqual(response_data['message'], "'initial' must be a list of numbers.")

    # 3. Successful `dp` Command
    @patch('src.mcp_server.perform_dp_calculation')
    @patch('src.mcp_server.get_initial_state')
    @patch('src.mcp_server.get_parameters')
    def test_successful_dp_command_minimal(self, mock_get_params, mock_get_state, mock_perform_dp):
        mock_params_obj = Parameters(DEFAULT_RATING_STEP, DEFAULT_K_COEFF, DEFAULT_MU)
        mock_state_obj = State.from_iterable([1500, 1500]) # Example state
        mock_dp_results = {"expected_value_int": 1600, "best_action_account_index": 0}

        mock_get_params.return_value = mock_params_obj
        mock_get_state.return_value = mock_state_obj
        mock_perform_dp.return_value = mock_dp_results

        request_data = {"command": "dp", "n": 10}
        self._simulate_post_request(MCP_PATH, data=request_data)

        mock_get_params.assert_called_once_with({
            "rating_step": DEFAULT_RATING_STEP,
            "k_coeff": DEFAULT_K_COEFF,
            "mu": DEFAULT_MU
        })
        mock_get_state.assert_called_once_with(DEFAULT_ACCOUNTS, None, mock_params_obj)
        mock_perform_dp.assert_called_once_with(10, mock_state_obj, mock_params_obj, DEFAULT_ACCOUNTS)
        
        self.mock_send_response.assert_called_once_with(200)
        response_data = self._get_response_data()
        self.assertEqual(response_data['status'], 'success')
        self.assertEqual(response_data['command'], 'dp')
        self.assertEqual(response_data['results'], mock_dp_results)

    @patch('src.mcp_server.perform_dp_calculation')
    @patch('src.mcp_server.get_initial_state')
    @patch('src.mcp_server.get_parameters')
    def test_successful_dp_command_all_params(self, mock_get_params, mock_get_state, mock_perform_dp):
        custom_params = {"rating_step": 32, "k_coeff": 0.005, "mu": 1600.0}
        custom_n = 20
        custom_accounts = 3
        custom_initial = [1500.0, 1550.0, 1600.0]

        mock_params_obj = Parameters(**custom_params)
        mock_state_obj = State.from_iterable([1500,1550,1600]) # Example, exact value not critical for test
        mock_dp_results = {"expected_value_int": 1700, "best_action_account_index": 1}

        mock_get_params.return_value = mock_params_obj
        mock_get_state.return_value = mock_state_obj
        mock_perform_dp.return_value = mock_dp_results

        request_data = {
            "command": "dp", 
            "n": custom_n,
            "accounts": custom_accounts,
            "initial": custom_initial,
            **custom_params
        }
        self._simulate_post_request(MCP_PATH, data=request_data)

        mock_get_params.assert_called_once_with(custom_params)
        mock_get_state.assert_called_once_with(custom_accounts, custom_initial, mock_params_obj)
        mock_perform_dp.assert_called_once_with(custom_n, mock_state_obj, mock_params_obj, custom_accounts)
        
        self.mock_send_response.assert_called_once_with(200)
        response_data = self._get_response_data()
        self.assertEqual(response_data['status'], 'success')
        self.assertEqual(response_data['results'], mock_dp_results)

    # 4. Successful `sim` Command
    @patch('src.mcp_server.perform_simulation')
    @patch('src.mcp_server.get_initial_state')
    @patch('src.mcp_server.get_parameters')
    def test_successful_sim_command_minimal(self, mock_get_params, mock_get_state, mock_perform_sim):
        mock_params_obj = Parameters(DEFAULT_RATING_STEP, DEFAULT_K_COEFF, DEFAULT_MU)
        mock_state_obj = State.from_iterable([1500, 1500])
        mock_sim_results = {"simulation_results": ["sim_res_1"], "visualization_files": []}

        mock_get_params.return_value = mock_params_obj
        mock_get_state.return_value = mock_state_obj
        mock_perform_sim.return_value = mock_sim_results
        
        request_data = {"command": "sim", "n": 50}
        self._simulate_post_request(MCP_PATH, data=request_data)

        mock_get_params.assert_called_once_with({
            "rating_step": DEFAULT_RATING_STEP,
            "k_coeff": DEFAULT_K_COEFF,
            "mu": DEFAULT_MU
        })
        mock_get_state.assert_called_once_with(DEFAULT_ACCOUNTS, None, mock_params_obj)
        mock_perform_sim.assert_called_once_with(
            50, mock_state_obj, mock_params_obj, DEFAULT_ACCOUNTS,
            DEFAULT_EPISODES, DEFAULT_POLICY, DEFAULT_FIXED_IDX, 
            DEFAULT_VISUALIZE, DEFAULT_OUTPUT_DIR
        )
        
        self.mock_send_response.assert_called_once_with(200)
        response_data = self._get_response_data()
        self.assertEqual(response_data['status'], 'success')
        self.assertEqual(response_data['command'], 'sim')
        self.assertEqual(response_data['results'], mock_sim_results)

    @patch('src.mcp_server.perform_simulation')
    @patch('src.mcp_server.get_initial_state')
    @patch('src.mcp_server.get_parameters')
    def test_successful_sim_command_all_params_visualize(self, mock_get_params, mock_get_state, mock_perform_sim):
        custom_params = {"rating_step": 8, "k_coeff": 0.001, "mu": 1400.0}
        custom_n = 30
        custom_accounts = 1
        custom_initial = [1450.0]
        custom_episodes = 500
        custom_policy = "greedy"
        custom_fixed_idx = 0 # Relevant if policy was "fixed"
        custom_visualize = True
        custom_output_dir = "/tmp/sim_output"

        mock_params_obj = Parameters(**custom_params)
        mock_state_obj = State.from_iterable([1450])
        mock_sim_results = {"simulation_results": ["res1"], "visualization_files": ["/tmp/sim_output/plot.png"]}

        mock_get_params.return_value = mock_params_obj
        mock_get_state.return_value = mock_state_obj
        mock_perform_sim.return_value = mock_sim_results

        request_data = {
            "command": "sim", "n": custom_n, "accounts": custom_accounts, "initial": custom_initial,
            "episodes": custom_episodes, "policy": custom_policy, "fixed_idx": custom_fixed_idx,
            "visualize": custom_visualize, "output_dir": custom_output_dir,
            **custom_params
        }
        self._simulate_post_request(MCP_PATH, data=request_data)

        mock_get_params.assert_called_once_with(custom_params)
        mock_get_state.assert_called_once_with(custom_accounts, custom_initial, mock_params_obj)
        mock_perform_sim.assert_called_once_with(
            custom_n, mock_state_obj, mock_params_obj, custom_accounts,
            custom_episodes, custom_policy, custom_fixed_idx, 
            custom_visualize, custom_output_dir
        )
        
        self.mock_send_response.assert_called_once_with(200)
        response_data = self._get_response_data()
        self.assertEqual(response_data['status'], 'success')
        self.assertEqual(response_data['results'], mock_sim_results)

    @patch('src.mcp_server.perform_simulation')
    @patch('src.mcp_server.get_initial_state')
    @patch('src.mcp_server.get_parameters')
    def test_sim_command_with_visualization_warning(self, mock_get_params, mock_get_state, mock_perform_sim):
        mock_params_obj = Parameters(DEFAULT_RATING_STEP, DEFAULT_K_COEFF, DEFAULT_MU)
        mock_state_obj = State.from_iterable([1500,1500])
        mock_sim_results_with_error = {
            "simulation_results": ["sim_res_1"], 
            "visualization_files": [],
            "error": "Matplotlib not found" # Error from perform_simulation
        }

        mock_get_params.return_value = mock_params_obj
        mock_get_state.return_value = mock_state_obj
        mock_perform_sim.return_value = mock_sim_results_with_error
        
        request_data = {"command": "sim", "n": 50, "visualize": True} # Visualize is true
        self._simulate_post_request(MCP_PATH, data=request_data)
        
        self.mock_send_response.assert_called_once_with(200)
        response_data = self._get_response_data()
        self.assertEqual(response_data['status'], 'success')
        self.assertEqual(response_data['results'], mock_sim_results_with_error)
        self.assertEqual(response_data['warning_visualization'], "Matplotlib not found")

    # 5. Error Handling from Core Logic
    @patch('src.mcp_server.get_initial_state')
    @patch('src.mcp_server.get_parameters')
    def test_error_get_initial_state_value_error(self, mock_get_params, mock_get_state):
        mock_get_params.return_value = Parameters(DEFAULT_RATING_STEP, DEFAULT_K_COEFF, DEFAULT_MU)
        mock_get_state.side_effect = ValueError("Test ValueError from get_initial_state")

        request_data = {"command": "dp", "n": 10, "initial": [1,2,3], "accounts": 2} # Mismatch
        self._simulate_post_request(MCP_PATH, data=request_data)

        self.mock_send_response.assert_called_once_with(400)
        response_data = self._get_response_data()
        self.assertEqual(response_data['status'], 'error')
        self.assertIn("Parameter validation error: Test ValueError from get_initial_state", response_data['message'])

    @patch('src.mcp_server.perform_dp_calculation')
    @patch('src.mcp_server.get_initial_state')
    @patch('src.mcp_server.get_parameters')
    def test_error_perform_dp_unhandled_exception(self, mock_get_params, mock_get_state, mock_perform_dp):
        mock_get_params.return_value = Parameters(DEFAULT_RATING_STEP, DEFAULT_K_COEFF, DEFAULT_MU)
        mock_get_state.return_value = State.from_iterable([1500,1500])
        mock_perform_dp.side_effect = Exception("Core logic boom!")

        request_data = {"command": "dp", "n": 10}
        self._simulate_post_request(MCP_PATH, data=request_data)

        self.mock_send_response.assert_called_once_with(500)
        response_data = self._get_response_data()
        self.assertEqual(response_data['status'], 'error')
        self.assertEqual(response_data['message'], "An unexpected server error occurred.")

    @patch('src.mcp_server.perform_simulation')
    @patch('src.mcp_server.get_initial_state')
    @patch('src.mcp_server.get_parameters')
    def test_error_perform_simulation_import_error(self, mock_get_params, mock_get_state, mock_perform_sim):
        mock_get_params.return_value = Parameters(DEFAULT_RATING_STEP, DEFAULT_K_COEFF, DEFAULT_MU)
        mock_get_state.return_value = State.from_iterable([1500,1500])
        # This error is now caught inside perform_simulation and returned in the dict.
        # The server should pass this through as a warning if visualize was true.
        # If the ImportError happens *outside* perform_simulation (e.g. for src.cli itself), then 500.
        # Let's test the case where perform_simulation itself raises ImportError (e.g. if it tried to import matplotlib directly at top level)
        # For the server to catch it as 500 for "missing dependency"
        
        mock_perform_sim.side_effect = ImportError("Mocked Matplotlib not found")

        request_data = {"command": "sim", "n": 10, "visualize": True}
        self._simulate_post_request(MCP_PATH, data=request_data)

        # The server's main try-except block for perform_simulation will catch this ImportError
        self.mock_send_response.assert_called_once_with(500)
        response_data = self._get_response_data()
        self.assertEqual(response_data['status'], 'error')
        self.assertIn("Server configuration error: Missing dependency for visualization.", response_data['message'])

if __name__ == '__main__':
    unittest.main()
