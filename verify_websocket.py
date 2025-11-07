#!/usr/bin/env python3
"""
WebSocket Implementation Verification Script

This script verifies that all WebSocket components are properly installed.
"""

import os
import sys
from pathlib import Path

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def check_file(filepath, description):
    """Check if a file exists."""
    exists = os.path.exists(filepath)
    status = f"{GREEN}✓{RESET}" if exists else f"{RED}✗{RESET}"
    print(f"{status} {description}: {filepath}")
    return exists

def main():
    print(f"{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}WebSocket Implementation Verification{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")

    all_good = True

    # Core implementation files
    print(f"{YELLOW}Core Implementation:{RESET}")
    all_good &= check_file("backend/handlers/websocket.go", "WebSocket Handler")
    all_good &= check_file("backend/main.go", "Main (with WebSocket routes)")
    all_good &= check_file("backend/services/queue.go", "Queue Service (with GetRedisClient)")
    print()

    # Test files
    print(f"{YELLOW}Test Files:{RESET}")
    all_good &= check_file("test_websocket.html", "HTML Test Client")
    all_good &= check_file("test_websocket_publish.py", "Python Test Publisher")
    print()

    # Documentation
    print(f"{YELLOW}Documentation:{RESET}")
    all_good &= check_file("WEBSOCKET_README.md", "WebSocket README")
    all_good &= check_file("WEBSOCKET_QUICKSTART.md", "Quick Start Guide")
    all_good &= check_file("WEBSOCKET_DOCUMENTATION.md", "Full Documentation")
    all_good &= check_file("WEBSOCKET_IMPLEMENTATION_SUMMARY.md", "Implementation Summary")
    print()

    # Check Go dependencies
    print(f"{YELLOW}Dependencies Check:{RESET}")
    go_mod_path = "backend/go.mod"
    if os.path.exists(go_mod_path):
        with open(go_mod_path, 'r') as f:
            content = f.read()
            has_websocket = "github.com/gofiber/websocket/v2" in content
            status = f"{GREEN}✓{RESET}" if has_websocket else f"{RED}✗{RESET}"
            print(f"{status} WebSocket dependency in go.mod")
            all_good &= has_websocket
    else:
        print(f"{RED}✗{RESET} go.mod not found")
        all_good = False
    print()

    # Check code snippets
    print(f"{YELLOW}Code Integration Check:{RESET}")
    
    # Check main.go has WebSocket routes
    main_go_path = "backend/main.go"
    if os.path.exists(main_go_path):
        with open(main_go_path, 'r') as f:
            content = f.read()
            has_ws_import = "github.com/gofiber/websocket/v2" in content
            has_ws_handler = "NewWebSocketHandler" in content
            has_ws_route = 'app.Get("/ws"' in content
            
            status1 = f"{GREEN}✓{RESET}" if has_ws_import else f"{RED}✗{RESET}"
            status2 = f"{GREEN}✓{RESET}" if has_ws_handler else f"{RED}✗{RESET}"
            status3 = f"{GREEN}✓{RESET}" if has_ws_route else f"{RED}✗{RESET}"
            
            print(f"{status1} WebSocket import in main.go")
            print(f"{status2} WebSocket handler initialization")
            print(f"{status3} /ws route registered")
            
            all_good &= has_ws_import and has_ws_handler and has_ws_route
    else:
        print(f"{RED}✗{RESET} main.go not found")
        all_good = False
    print()

    # Check queue.go has GetRedisClient
    queue_go_path = "backend/services/queue.go"
    if os.path.exists(queue_go_path):
        with open(queue_go_path, 'r') as f:
            content = f.read()
            has_method = "GetRedisClient()" in content
            status = f"{GREEN}✓{RESET}" if has_method else f"{RED}✗{RESET}"
            print(f"{status} GetRedisClient() method in queue.go")
            all_good &= has_method
    else:
        print(f"{RED}✗{RESET} queue.go not found")
        all_good = False
    print()

    # Feature checklist
    print(f"{YELLOW}Feature Checklist:{RESET}")
    websocket_go_path = "backend/handlers/websocket.go"
    if os.path.exists(websocket_go_path):
        with open(websocket_go_path, 'r') as f:
            content = f.read()
            
            features = [
                ("Client Management (sync.RWMutex)", "sync.RWMutex" in content),
                ("Redis Pub/Sub", "subscribeToRedis" in content),
                ("Broadcasting", "broadcast" in content),
                ("Ping/Pong", "PingMessage" in content),
                ("Client Disconnect", "unregister" in content),
                ("Message Format", "WebSocketMessage" in content),
                ("Statistics Endpoint", "GetStats" in content),
            ]
            
            for feature, check in features:
                status = f"{GREEN}✓{RESET}" if check else f"{RED}✗{RESET}"
                print(f"{status} {feature}")
                all_good &= check
    else:
        print(f"{RED}✗{RESET} websocket.go not found")
        all_good = False
    print()

    # Summary
    print(f"{BLUE}{'='*70}{RESET}")
    if all_good:
        print(f"{GREEN}✓ ALL CHECKS PASSED!{RESET}")
        print(f"\n{YELLOW}Next Steps:{RESET}")
        print(f"  1. cd backend && go run main.go")
        print(f"  2. Open test_websocket.html in browser")
        print(f"  3. python test_websocket_publish.py")
        print(f"\n{YELLOW}Documentation:{RESET}")
        print(f"  - Quick Start: WEBSOCKET_QUICKSTART.md")
        print(f"  - Full Docs:   WEBSOCKET_DOCUMENTATION.md")
        print(f"  - Summary:     WEBSOCKET_README.md")
    else:
        print(f"{RED}✗ SOME CHECKS FAILED{RESET}")
        print(f"\nPlease review the errors above.")
    print(f"{BLUE}{'='*70}{RESET}")
    
    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main())
