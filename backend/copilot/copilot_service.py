"""
Service layer for interacting with Groq via the Copilot tools.
"""
import os
import json
from groq import Groq
from sqlalchemy.orm import Session
from fastapi import HTTPException

from .tools import TOOL_DEFINITIONS, TOOL_DISPATCH

class CopilotService:
    def __init__(self):
        # We don't fail immediately on init if the key is missing, 
        # so the rest of the backend still works
        self.api_key = os.environ.get("GROQ_API_KEY")
        self.model_name = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
        self.client = None
        if self.api_key:
            self.client = Groq(api_key=self.api_key)
            
    def chat(self, message: str, case_id: str, db: Session) -> dict:
        if not self.client:
            return {
                "reply": "Groq Copilot is currently unavailable. Please configure the GROQ_API_KEY environment variable.",
                "tool_calls": [],
                "sources": [],
                "error": "api_key_missing"
            }
            
        system_prompt = (
            "You are BhoomiDrishti Copilot, an AI assistant for a geospatial change-detection portal. "
            "Your job is to answer questions about detected changes, land parcels, and cases. "
            "You MUST use the provided tools to fetch factual data from the database. "
            "Never invent or hallucinate data like case IDs, coordinates, areas, severity scores, or classifications. "
            "If the tools return 'not_analyzed' or missing data, explicitly state that the data is unavailable. "
            "When referencing a case, mention its Case Number."
        )
        
        if case_id:
            system_prompt += f"\nThe user is currently looking at Case ID: {case_id}. You should prioritize this context."
            
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
        
        try:
            # 1. Initial request with tools
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                max_tokens=1024,
                temperature=0.1
            )
            
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls
            
            executed_tools = []
            
            # 2. If no tools called, return the response directly
            if not tool_calls:
                return {
                    "reply": response_message.content,
                    "tool_calls": [],
                    "sources": []
                }
                
            # 3. Execute tools and append results
            messages.append({
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
                    } for tc in tool_calls
                ]
            })
            
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                # Execute the actual function
                if function_name in TOOL_DISPATCH:
                    try:
                        # Ensure 'db' is passed implicitly if not in args
                        if "db" not in function_args:
                            function_args["db"] = db
                        function_response = TOOL_DISPATCH[function_name](**function_args)
                        
                        executed_tools.append({
                            "name": function_name,
                            "args": tool_call.function.arguments,
                            "result": "success" if "error" not in function_response else "error"
                        })
                        
                    except Exception as e:
                        function_response = {"error": f"Tool execution failed: {str(e)}"}
                else:
                    function_response = {"error": f"Tool '{function_name}' not found."}
                    
                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(function_response),
                    }
                )
                
            # 4. Final generation with tool results
            second_response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=1024,
                temperature=0.2
            )
            
            return {
                "reply": second_response.choices[0].message.content,
                "tool_calls": executed_tools,
                "sources": [tc["name"] for tc in executed_tools]
            }
            
        except Exception as e:
            print(f"Copilot API error: {e}")
            return {
                "reply": "I encountered an error while trying to process your request.",
                "tool_calls": [],
                "sources": [],
                "error": str(e)
            }

copilot_service_instance = CopilotService()

def get_copilot_service():
    return copilot_service_instance
