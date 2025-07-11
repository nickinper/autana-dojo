#!/usr/bin/env python3
"""
Bridge between Autana Dojo and Claude Avatar System
Enables seamless communication between taskbar and intelligence layer
"""

import json
import asyncio
import websockets
from typing import Dict, Any, Optional
import subprocess
import os
import sys

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from intelligence_layer.sakana_intelligence import SakanaIntelligenceLayer
from privilege_manager.privilege_system import PrivilegeLevel


class AvatarBridge:
    """Bridge between Avatar taskbar and Dojo intelligence"""
    
    def __init__(self, intelligence: Optional[SakanaIntelligenceLayer] = None):
        self.intelligence = intelligence or SakanaIntelligenceLayer()
        self.avatar_specialists = {}
        self.websocket_port = 8765
        self.ipc_pipe = "/tmp/autana_dojo_avatar_bridge"
        
    async def start_websocket_server(self):
        """Start WebSocket server for Avatar communication"""
        print(f"🌐 Starting Avatar Bridge on port {self.websocket_port}")
        
        async def handler(websocket, path):
            try:
                async for message in websocket:
                    response = await self.process_avatar_message(json.loads(message))
                    await websocket.send(json.dumps(response))
            except Exception as e:
                print(f"Error in WebSocket handler: {e}")
        
        await websockets.serve(handler, "localhost", self.websocket_port)
        print(f"✅ Avatar Bridge ready at ws://localhost:{self.websocket_port}")
    
    async def process_avatar_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process message from Avatar taskbar"""
        
        command = message.get("command")
        params = message.get("params", {})
        
        print(f"📨 Received from Avatar: {command}")
        
        # Command routing
        if command == "train":
            return await self.handle_train_request(params)
        
        elif command == "transform":
            return await self.handle_transform_request(params)
        
        elif command == "find_pattern":
            return await self.handle_pattern_discovery(params)
        
        elif command == "deploy":
            return await self.handle_deployment_request(params)
        
        elif command == "query":
            return await self.handle_intelligence_query(params)
        
        elif command == "status":
            return self.get_bridge_status()
        
        else:
            return {
                "error": f"Unknown command: {command}",
                "available_commands": [
                    "train", "transform", "find_pattern", 
                    "deploy", "query", "status"
                ]
            }
    
    async def handle_train_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle training request from Avatar"""
        
        task_type = params.get("type", "general")
        description = params.get("description", "")
        priority = params.get("priority", "medium")
        
        # Add to Dojo queue
        task_id = self.intelligence.add_task_to_queue(
            description=description,
            domain=task_type,
            priority=priority
        )
        
        # Process immediately if high priority
        if priority == "high":
            self.intelligence.process_queue()
        
        return {
            "status": "success",
            "task_id": task_id,
            "message": f"Training task queued: {description[:50]}...",
            "specialist_available": task_type in self.avatar_specialists
        }
    
    async def handle_transform_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle avatar transformation request"""
        
        avatar_mode = params.get("mode", "guide")
        input_data = params.get("input", "")
        
        # Get intelligence from appropriate specialist
        result = self.intelligence.bridge_to_claude_avatar(avatar_mode, input_data)
        
        # Transform result for avatar display
        avatar_response = {
            "mode": avatar_mode,
            "emoji": self._get_avatar_emoji(avatar_mode),
            "response": result.get("output", ""),
            "patterns_used": result.get("patterns_applied", 0),
            "confidence": result.get("details", [{}])[0].get("confidence", 0.5)
        }
        
        return avatar_response
    
    async def handle_pattern_discovery(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Discover patterns in provided data"""
        
        data = params.get("data", [])
        field = params.get("field", None)
        
        if not data:
            return {"error": "No data provided for pattern discovery"}
        
        # Use pattern engine
        discoveries = self.intelligence.pattern_engine.discover_pattern(data, field)
        
        # Format for avatar display
        return {
            "status": "success",
            "discoveries": discoveries["discoveries"],
            "best_pattern": discoveries["best_pattern"],
            "visualization": self._create_pattern_visualization(discoveries)
        }
    
    async def handle_deployment_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle model deployment request"""
        
        specialist_name = params.get("specialist", "")
        target = params.get("target", "local")  # local, api, production
        
        # Find specialist
        specialist_id = None
        for sid, spec in self.intelligence.active_specialists.items():
            if spec["name"] == specialist_name:
                specialist_id = sid
                break
        
        if not specialist_id:
            return {"error": f"Specialist '{specialist_name}' not found"}
        
        # Check deployment privileges
        can_deploy = self.intelligence.privilege_system.check_privilege(
            self.intelligence.active_specialists[specialist_id]["model_id"],
            "deployment"
        )
        
        if not can_deploy:
            # Request escalation
            request_id = self.intelligence.privilege_system.request_privilege_escalation(
                self.intelligence.active_specialists[specialist_id]["model_id"],
                PrivilegeLevel.DESKTOP,
                "Deployment requested via Avatar",
                "avatar_user"
            )
            
            return {
                "status": "privilege_required",
                "message": "Specialist needs deployment privileges",
                "escalation_request": request_id
            }
        
        # Deploy based on target
        if target == "local":
            return self._deploy_local(specialist_id)
        elif target == "api":
            return self._create_api_endpoint(specialist_id)
        else:
            return {"error": f"Unknown deployment target: {target}"}
    
    async def handle_intelligence_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Query intelligence layer for information"""
        
        query_type = params.get("type", "stats")
        
        if query_type == "stats":
            return self.intelligence.get_intelligence_stats()
        
        elif query_type == "specialists":
            return {
                "specialists": [
                    {
                        "id": sid,
                        "name": spec["name"],
                        "domain": spec["domain"],
                        "patterns": len(spec["patterns"]),
                        "privilege": spec["privilege_level"].value
                    }
                    for sid, spec in self.intelligence.active_specialists.items()
                ]
            }
        
        elif query_type == "discoveries":
            # Get recent discoveries from database
            return self._get_recent_discoveries()
        
        else:
            return {"error": f"Unknown query type: {query_type}"}
    
    def get_bridge_status(self) -> Dict[str, Any]:
        """Get current bridge status"""
        
        return {
            "status": "active",
            "connected_avatars": len(self.avatar_specialists),
            "intelligence_layer": "online",
            "websocket_port": self.websocket_port,
            "active_specialists": len(self.intelligence.active_specialists),
            "privilege_system": "enabled"
        }
    
    def _get_avatar_emoji(self, mode: str) -> str:
        """Get emoji for avatar mode"""
        
        emoji_map = {
            "guide": "🧭",
            "explorer": "🔮",
            "builder": "🏗️",
            "synthesizer": "🧬",
            "debugger": "🔍",
            "oracle": "🎲",
            "muse": "🎨"
        }
        
        return emoji_map.get(mode, "🤖")
    
    def _create_pattern_visualization(self, discoveries: Dict) -> str:
        """Create ASCII visualization of pattern"""
        
        if not discoveries["best_pattern"]:
            return "No patterns found"
        
        pattern = discoveries["best_pattern"]
        
        # Simple ASCII art based on pattern type
        if pattern["pattern"] == "fibonacci":
            return "1→1→2→3→5→8→13→..."
        elif pattern["pattern"] == "modular":
            return "x % m = c (constant)"
        elif pattern["pattern"] == "ratio":
            return f"×{pattern.get('formula', '').split('*')[-1] if '*' in pattern.get('formula', '') else '?'}"
        elif pattern["pattern"] == "chaotic":
            return "🌀 Chaotic attractor detected"
        else:
            return f"Pattern: {pattern['pattern']}"
    
    def _deploy_local(self, specialist_id: str) -> Dict[str, Any]:
        """Deploy specialist locally"""
        
        # Create deployment script
        deployment_path = f"/tmp/specialist_{specialist_id}.py"
        
        specialist = self.intelligence.active_specialists[specialist_id]
        
        script_content = f'''#!/usr/bin/env python3
"""
Auto-generated specialist: {specialist["name"]}
Domain: {specialist["domain"]}
Patterns: {len(specialist["patterns"])}
"""

import json

patterns = {json.dumps(specialist["patterns"], indent=2)}

def process(input_data):
    # Apply patterns
    result = input_data
    for pattern in patterns:
        # Pattern application logic here
        pass
    return result

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        input_val = float(sys.argv[1])
        print(f"Result: {{process(input_val)}}")
'''
        
        with open(deployment_path, 'w') as f:
            f.write(script_content)
        
        os.chmod(deployment_path, 0o755)
        
        return {
            "status": "deployed",
            "path": deployment_path,
            "specialist": specialist["name"],
            "message": f"Specialist deployed to {deployment_path}"
        }
    
    def _create_api_endpoint(self, specialist_id: str) -> Dict[str, Any]:
        """Create API endpoint for specialist"""
        
        specialist = self.intelligence.active_specialists[specialist_id]
        
        # Generate API configuration
        api_config = {
            "endpoint": f"/api/v1/specialists/{specialist['name']}",
            "method": "POST",
            "input_schema": {
                "type": "object",
                "properties": {
                    "data": {"type": "number"},
                    "options": {"type": "object"}
                }
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "result": {"type": "number"},
                    "patterns_applied": {"type": "integer"},
                    "confidence": {"type": "number"}
                }
            }
        }
        
        return {
            "status": "api_ready",
            "config": api_config,
            "curl_example": f"curl -X POST http://localhost:8000{api_config['endpoint']} -d '{{\"data\": 100}}'"
        }
    
    def _get_recent_discoveries(self) -> Dict[str, Any]:
        """Get recent pattern discoveries"""
        
        # This would query the database
        # For demo, return mock data
        return {
            "recent_discoveries": [
                {
                    "pattern": "fibonacci_variant",
                    "field": "arithmetic",
                    "confidence": 0.92,
                    "discovered": "2 minutes ago"
                },
                {
                    "pattern": "chaos_attractor",
                    "field": "dynamics",
                    "confidence": 0.78,
                    "discovered": "5 minutes ago"
                }
            ]
        }


class AvatarIPCBridge:
    """IPC bridge for direct Avatar-Dojo communication"""
    
    def __init__(self, intelligence: SakanaIntelligenceLayer):
        self.intelligence = intelligence
        self.pipe_path = "/tmp/autana_dojo_ipc"
        
    def start_ipc_listener(self):
        """Start IPC listener for Avatar commands"""
        
        # Create named pipe if not exists
        if not os.path.exists(self.pipe_path):
            os.mkfifo(self.pipe_path)
        
        print(f"📡 IPC Bridge listening at {self.pipe_path}")
        
        while True:
            with open(self.pipe_path, 'r') as pipe:
                command = pipe.read().strip()
                if command:
                    response = self.process_ipc_command(command)
                    # Write response back
                    with open(f"{self.pipe_path}.response", 'w') as resp:
                        resp.write(json.dumps(response))
    
    def process_ipc_command(self, command: str) -> Dict[str, Any]:
        """Process IPC command from Avatar"""
        
        try:
            cmd_data = json.loads(command)
            # Route to appropriate handler
            if cmd_data.get("type") == "quick_query":
                return {"result": "instant_response"}
            else:
                return {"error": "Unknown IPC command"}
        except:
            return {"error": "Invalid command format"}


async def run_avatar_bridge():
    """Run the Avatar bridge server"""
    
    print("🌉 Starting Autana Dojo - Claude Avatar Bridge")
    print("=" * 60)
    
    # Initialize bridge
    bridge = AvatarBridge()
    
    # Start WebSocket server
    await bridge.start_websocket_server()
    
    # Keep running
    await asyncio.Future()  # Run forever


if __name__ == "__main__":
    # Run bridge
    asyncio.run(run_avatar_bridge())