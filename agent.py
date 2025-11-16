import os
import json
import asyncio
from typing import List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
from agent_tools import TOOLS, execute_tool, cleanup

# Load environment variables
load_dotenv()
verbose = True # Set to true to print tool calls, args, and results

class MapAgent:
    """Agent that uses MCP map servers to answer user queries"""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL")
        self.conversation_history: List[Dict[str, Any]] = []
        self.verbose = verbose
        
    def _get_system_prompt(self) -> str:
        """Gets the system prompt with context about the available tools"""
        with open("agent_prompt.txt", "r") as file:
            return file.read()
    
    async def chat(self, user_message: str) -> str:
        """
        Process a user message and return the agent's response.
        Handles tool calls automatically.
        """
        # Add user message to history
        self.conversation_history.append({"role": "user","content": user_message})
        
        # Prepare messages with system message
        messages = [{"role": "system", "content": self._get_system_prompt()}] + self.conversation_history
        
        # Initial API call
        response = self.client.chat.completions.create(model=self.model, messages=messages, tools=TOOLS, tool_choice="auto")
        response_message = response.choices[0].message
        
        # Handle tool calls
        while response_message.tool_calls:
            # Add assistant's response with tool calls to history
            self.conversation_history.append({
                "role": "assistant",
                "content": response_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in response_message.tool_calls
                ]
            })
            
            # Execute each tool call
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                if self.verbose:
                    print("\n--------------------------------")
                    print(f"\nCalling tool: {function_name}")
                    print(f"   Arguments: {json.dumps(function_args, indent=2)}")
                    
                # Execute the tool
                function_response = await execute_tool(function_name, function_args)
                if self.verbose:
                    print(f"   Result: {json.dumps(function_response, indent=2)[:200]}...")
                    print("--------------------------------\n")
                
                # Add tool response to history
                self.conversation_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(function_response)
                })
            
            # Get next response from the model
            messages = [{"role": "system", "content": self._get_system_prompt()}] + self.conversation_history
            
            response = self.client.chat.completions.create(model=self.model, messages=messages, tools=TOOLS, tool_choice="auto")
            
            response_message = response.choices[0].message
        
        # Add final assistant response to history
        assistant_message = response_message.content or "I apologize, but I couldn't generate a response."
        self.conversation_history.append({"role": "assistant", "content": assistant_message})
        
        return assistant_message
    
    def reset_conversation(self):
        """Clear conversation history"""
        self.conversation_history = []


async def main():
    """Main interactive loop"""
    agent = MapAgent()
    
    print("=" * 60)
    print("Map Agent")
    print("-" * 60)
    print("Using model: ", agent.model, "with verbose: ", agent.verbose)
    print("Type 'exit' to end the conversation.")
    print("Type 'reset' to start a new conversation.")
    print("=" * 60)
    print("Example queries:")
    print("Where is Times Square in New York City?")
    print("What's at coordinates 33.8980915, 35.5649815?")
    print("How do I get from Times Square to Central Park by walking?")
    print("What are my most frequently visited places of all time?")
    print("Show me my travel statistics overall all time.")
    print("What's the weather like in Beirut today?")
    print("What's the air quality like in Beirut today?")
    print("What's the astronomy like in Beirut today?")
    print("\nOr any complex combination/scenario of the above queries.")
    print("=" * 60)
    
    try:
        while True:
            user_input = input("\nUser: ").strip()
            
            if user_input.lower() == 'exit':
                print("\nExited.")
                break
            
            if user_input.lower() == 'reset':
                agent.reset_conversation()
                print("\nConversation reset.")
                continue
            
            if not user_input:
                continue
            
            print("\nAgent: ", end="", flush=True)
            response = await agent.chat(user_input)
            print(response)
    
    finally:
        # Cleanup resources
        await cleanup()


if __name__ == "__main__":
    asyncio.run(main())