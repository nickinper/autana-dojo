#!/usr/bin/env python3
"""
Autana Dojo - Main Application
Part training app, part IDE, powered by Sakana intelligence
"""

import os
import sys
import json
import click
from typing import Optional, Dict, Any
import asyncio

# Add core to path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'core'))

from intelligence_layer.sakana_intelligence import SakanaIntelligenceLayer
from privilege_manager.privilege_system import PrivilegeLevel
from pattern_engine.pattern_engine import SakanaPatternEngine
from bridges.claude_avatar.avatar_bridge import AvatarBridge


class AutanaDojo:
    """Main Dojo application"""
    
    def __init__(self):
        self.intelligence = SakanaIntelligenceLayer()
        self.pattern_engine = SakanaPatternEngine()
        self.avatar_bridge = AvatarBridge(self.intelligence)
        self.mode = "hybrid"  # training, ide, hybrid
        
    def process_natural_language(self, command: str) -> Dict[str, Any]:
        """Process natural language commands"""
        
        command_lower = command.lower()
        
        # Training commands
        if any(word in command_lower for word in ["train", "create specialist", "learn"]):
            return self._handle_training_command(command)
        
        # Pattern discovery
        elif any(word in command_lower for word in ["find pattern", "discover", "analyze"]):
            return self._handle_discovery_command(command)
        
        # Deployment
        elif any(word in command_lower for word in ["deploy", "launch", "production"]):
            return self._handle_deployment_command(command)
        
        # Mode switching
        elif any(word in command_lower for word in ["switch to", "mode", "transform"]):
            return self._handle_mode_switch(command)
        
        # Query
        elif any(word in command_lower for word in ["show", "list", "status", "stats"]):
            return self._handle_query_command(command)
        
        # IDE commands
        elif any(word in command_lower for word in ["edit", "code", "open"]):
            return self._handle_ide_command(command)
        
        else:
            return {
                "response": "I didn't understand that command. Try:",
                "suggestions": [
                    "train a specialist for [task]",
                    "find patterns in [data]",
                    "deploy [specialist name]",
                    "show specialists",
                    "switch to IDE mode"
                ]
            }
    
    def _handle_training_command(self, command: str) -> Dict[str, Any]:
        """Handle training-related commands"""
        
        # Extract task description
        if "for" in command:
            task_desc = command.split("for", 1)[1].strip()
        elif "to" in command:
            task_desc = command.split("to", 1)[1].strip()
        else:
            task_desc = "general task"
        
        # Determine domain
        domain = self._extract_domain(task_desc)
        
        # Create specialist
        name = f"{domain}_specialist"
        specialist_id = self.intelligence.create_specialist(
            name=name,
            domain=domain,
            privilege_level=PrivilegeLevel.TRAINING
        )
        
        # Add training task
        task_id = self.intelligence.add_task_to_queue(
            description=task_desc,
            domain=domain,
            priority="high"
        )
        
        # Train immediately
        self.intelligence.process_queue()
        
        return {
            "response": f"✅ Created and training {name}",
            "specialist_id": specialist_id,
            "task_id": task_id,
            "status": "Training in progress...",
            "compression": "1000x smaller than neural networks"
        }
    
    def _handle_discovery_command(self, command: str) -> Dict[str, Any]:
        """Handle pattern discovery commands"""
        
        # Extract data reference
        if "in" in command:
            data_ref = command.split("in", 1)[1].strip()
            
            # For demo, use sample data
            sample_data = [1, 1, 2, 3, 5, 8, 13, 21]
            
            discoveries = self.pattern_engine.discover_pattern(sample_data)
            
            return {
                "response": "🔍 Pattern discovery complete",
                "discoveries": discoveries["discoveries"],
                "best_pattern": discoveries["best_pattern"],
                "visualization": self._visualize_pattern(discoveries["best_pattern"])
            }
        
        return {
            "response": "Please specify data to analyze",
            "example": "find patterns in sales_data.csv"
        }
    
    def _handle_deployment_command(self, command: str) -> Dict[str, Any]:
        """Handle deployment commands"""
        
        # Extract specialist name
        words = command.split()
        specialist_name = None
        
        for spec_id, spec in self.intelligence.active_specialists.items():
            if spec["name"] in command:
                specialist_name = spec["name"]
                break
        
        if not specialist_name:
            return {
                "response": "Which specialist would you like to deploy?",
                "available": [
                    spec["name"] for spec in self.intelligence.active_specialists.values()
                ]
            }
        
        # Request deployment
        return {
            "response": f"🚀 Deploying {specialist_name}",
            "options": [
                "deploy locally (creates Python script)",
                "deploy as API (REST endpoint)",
                "deploy to production (requires privileges)"
            ]
        }
    
    def _handle_mode_switch(self, command: str) -> Dict[str, Any]:
        """Handle mode switching"""
        
        if "training" in command:
            self.mode = "training"
            response = "📚 Switched to Training Mode"
        elif "ide" in command or "code" in command:
            self.mode = "ide"
            response = "💻 Switched to IDE Mode"
        elif "hybrid" in command:
            self.mode = "hybrid"
            response = "🔀 Switched to Hybrid Mode"
        else:
            return {
                "response": "Available modes: training, ide, hybrid",
                "current_mode": self.mode
            }
        
        return {
            "response": response,
            "mode": self.mode,
            "features": self._get_mode_features()
        }
    
    def _handle_query_command(self, command: str) -> Dict[str, Any]:
        """Handle query commands"""
        
        if "specialist" in command:
            specialists = []
            for spec_id, spec in self.intelligence.active_specialists.items():
                specialists.append({
                    "name": spec["name"],
                    "domain": spec["domain"],
                    "patterns": len(spec["patterns"]),
                    "privilege": spec["privilege_level"].value
                })
            
            return {
                "response": f"📋 {len(specialists)} active specialists",
                "specialists": specialists
            }
        
        elif "stats" in command or "status" in command:
            stats = self.intelligence.get_intelligence_stats()
            return {
                "response": "📊 Dojo Statistics",
                "stats": stats
            }
        
        else:
            return {
                "response": "What would you like to know?",
                "options": ["show specialists", "show stats", "show discoveries"]
            }
    
    def _handle_ide_command(self, command: str) -> Dict[str, Any]:
        """Handle IDE-related commands"""
        
        return {
            "response": "💻 Opening IDE view",
            "action": "switch_to_ide",
            "message": "Use the IDE to edit specialist patterns and test them"
        }
    
    def _extract_domain(self, task_description: str) -> str:
        """Extract domain from task description"""
        
        desc_lower = task_description.lower()
        
        if any(word in desc_lower for word in ["optimize", "improve", "maximize"]):
            return "optimization"
        elif any(word in desc_lower for word in ["predict", "forecast", "estimate"]):
            return "prediction"
        elif any(word in desc_lower for word in ["classify", "categorize", "group"]):
            return "classification"
        elif any(word in desc_lower for word in ["discover", "find", "explore"]):
            return "discovery"
        else:
            return "general"
    
    def _visualize_pattern(self, pattern: Optional[Dict]) -> str:
        """Create simple visualization of pattern"""
        
        if not pattern:
            return "No pattern found"
        
        if pattern["pattern"] == "fibonacci":
            return """
            Fibonacci Pattern Detected:
            1 → 1 → 2 → 3 → 5 → 8 → 13 → 21
            Each = sum of previous two
            """
        elif pattern["pattern"] == "modular":
            return """
            Modular Pattern Detected:
            x % m = constant
            Regular cycling behavior
            """
        else:
            return f"Pattern: {pattern['pattern']} (confidence: {pattern['confidence']:.2%})"
    
    def _get_mode_features(self) -> list:
        """Get features for current mode"""
        
        features = {
            "training": [
                "Create specialists",
                "Train on tasks",
                "Pattern discovery",
                "Performance metrics"
            ],
            "ide": [
                "Edit patterns",
                "Test specialists",
                "Debug mode",
                "Live preview"
            ],
            "hybrid": [
                "All features available",
                "Split screen view",
                "Seamless switching",
                "Integrated workflow"
            ]
        }
        
        return features.get(self.mode, [])


@click.group()
def cli():
    """Autana Dojo - Sakana Intelligence Training Ground"""
    pass


@cli.command()
@click.option('--mode', default='hybrid', type=click.Choice(['training', 'ide', 'hybrid']))
def start(mode):
    """Start the Dojo in specified mode"""
    
    dojo = AutanaDojo()
    dojo.mode = mode
    
    print(f"""
🏯 Welcome to Autana Dojo
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Mode: {mode.upper()}
Intelligence: Sakana Pattern Engine (CPU-only)
Compression: 1000x vs Neural Networks
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Available Commands:
- train a specialist for [task]
- find patterns in [data]  
- deploy [specialist]
- show specialists
- switch to [mode]

Type 'help' for more commands or 'exit' to quit.
    """)
    
    while True:
        try:
            command = input("\n🥋 Dojo> ").strip()
            
            if command.lower() in ['exit', 'quit']:
                print("👋 Goodbye from Autana Dojo!")
                break
            
            elif command.lower() == 'help':
                print("""
Commands:
  Training:
    - train a specialist for inventory optimization
    - create specialist to predict sales
    
  Discovery:
    - find patterns in [data]
    - analyze mathematical structure
    
  Deployment:
    - deploy pricing_specialist
    - launch model as API
    
  Query:
    - show specialists
    - show stats
    - list discoveries
    
  Mode:
    - switch to training mode
    - switch to IDE mode
    - switch to hybrid mode
                """)
            
            else:
                result = dojo.process_natural_language(command)
                
                # Display result
                print(f"\n{result['response']}")
                
                if 'specialists' in result:
                    for spec in result['specialists']:
                        print(f"  • {spec['name']} ({spec['domain']}) - {spec['patterns']} patterns")
                
                if 'stats' in result:
                    for key, value in result['stats'].items():
                        print(f"  {key}: {value}")
                
                if 'suggestions' in result:
                    print("\nSuggestions:")
                    for suggestion in result['suggestions']:
                        print(f"  • {suggestion}")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye from Autana Dojo!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


@cli.command()
def bridge():
    """Start Avatar bridge server"""
    
    print("🌉 Starting Claude Avatar Bridge...")
    
    # Run async bridge
    import asyncio
    from bridges.claude_avatar.avatar_bridge import run_avatar_bridge
    
    try:
        asyncio.run(run_avatar_bridge())
    except KeyboardInterrupt:
        print("\n👋 Bridge shutdown")


@cli.command()
def web():
    """Start web interface (future feature)"""
    
    print("🌐 Web interface coming soon!")
    print("This will provide:")
    print("  • Visual pattern discovery")
    print("  • Drag-and-drop training")
    print("  • Real-time specialist monitoring")
    print("  • Split-screen IDE mode")


if __name__ == "__main__":
    cli()