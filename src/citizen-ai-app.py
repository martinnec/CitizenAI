from typing import Any, List
from pydantic import BaseModel
import asyncio
import uuid
import json

from agents import (
    Agent,
    HandoffOutputItem,
    ItemHelpers,
    MessageOutputItem,
    RunContextWrapper,
    Runner,
    ToolCallItem,
    ToolCallOutputItem,
    TResponseInputItem,
    function_tool,
    WebSearchTool
)
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

from stores.government_services_store import GovernmentServicesStore, GovernmentService

store = GovernmentServicesStore()
store.load_services()

class CitizenContext(BaseModel):
    citizen_name: str | None = None
    citizen_age: int | None = None

@function_tool
async def service_lookup_tool_keywords(keywords: List[str], k: int) -> List[GovernmentService]:
    """
    Search for government services based on exactly matching keywords.
    Keywords must be in Czech.
    For better search performance, use not only key-phrases but also individual keywords.
    The number of keywords is not limited, the more keywords, the better the search results. However, beware too generic keywords, as they may return too many results.
    If more services are needed, the `k` parameter can be adjusted to return more results and also the list of keywords can be adjusted to include more relevant terms. The keywords should be relevant to the life situation described by the citizen.
    
    :param keywords: List of keywords to search for.
    :param k: Number of top results to return.
    :return: List of top-K GovernmentService objects matching the keywords.
    """
    services = store.search_services_by_keywords(keywords, k)
    print("[DEBUG] TOOL service_lookup_tool_keywords: Found services by keywords", [service.name for service in services])
    return services

@function_tool
async def service_lookup_tool_semantic(life_situation_text: str, k: int) -> List[GovernmentService]:
    """
    Search for government services based on the described life situation.
    If more services are needed, the `k` parameter can be adjusted to return more results and also the list of keywords can be adjusted to include more relevant terms. The keywords should be relevant to the life situation described by the citizen.
    
    :param life_situation_text: Description of the life situation.
    :param k: Number of top results to return.
    :return: List of top-K GovernmentService objects matching the life situation.
    """
    services = store.search_services_semantically(life_situation_text, k)
    print("[DEBUG] TOOL service_lookup_tool_semantic: Found services by life situation:", [service.name for service in services])
    return services

@function_tool
async def service_detail_tool(service_id: str) -> str:
    """
    Get detailed information about a specific service by its ID.
    
    :param service_id: The ID of the service to retrieve details for.
    :return: A string containing the detailed information about the service.
    """
    print("[DEBUG] TOOL service_detail_tool: Asking for service detail: ", service_id)
    service_detail_str = store.get_service_detail_by_id(service_id)
    if service_detail_str:
        return service_detail_str
    else:
        return "Service not found."
    
@function_tool
async def service_steps_tool(service_id: str) -> str:
    """
    Get the steps needed to resolve a citizen's life situation using a specific government service.
    
    :param service_id: The ID of the service to retrieve steps for.
    :return: A list of steps needed to resolve the citizen's life situation using the service.
    """
    print("[DEBUG] TOOL service_steps_tool: Asking for service steps: ", service_id)
    steps = store.get_service_steps_by_id(service_id)
    if steps:
        # Serialize steps into a single string as a numbered list
        step_str = "\n".join([f"{i+1}. {step}" for i, step in enumerate(steps)])
        return "**STEPS**:\n" + step_str + "\n\n**ADIDITIONAL INFORMATION TO PERFORM THE STEPS**:\n" + store.get_service_howto_by_id(service_id)
    else:
        return ["No steps found for this service."]

###
#service_lookup_agent_keywords = Agent[CitizenContext](
#    name="Service Lookup by Keywords Agent",
#    handoff_description="A helpful agent that can find government services based on citizens's life situation.",
#    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
#    You are a government service lookup agent. You were transferred from the triage agent because the citizen describes their life situation they need to help with.
#    The citizen speaks Czech, you answer in Czech.
#    Call the citizen by their name and augment the messages to the citizen appropriately their age, based on the context.
#    Use the following routine to support the citizen:
#    # Routine
#    1. Identify the keywords that best characterize the citizen's life situation. These keywords should be short and specific, preferably single words, not keyphrases. Use at least 10 keywords to have a chance to find something.
#    2. Use the `service_lookup_tool_keywords` to search for government services based on the identified keywords. It is recommended to set the `k` parameter to 10, but it can be adjusted to return more results if needed.
#    3. If you find no service, ask the citizen to better specify their life situation and repeat the routine from step 1.
#    4. If you find services, check if they are relevant to the citizen's problem by comparing their descriptions with the citizen's life situation.
#    5. If there is no relevant service, ask the citizen to better specify their life situation and repeat the routine from step 1.
#    6. List the relevant services to the citizen, including their names, IDs and short explanations of how they can help the citizen in their life situation.
#    7. If the citizen needs more detailed information about a specific service, transfer back to the triage agent.
#    """,
#    tools=[service_lookup_tool_keywords],
#    model="gpt-4o"
#)

service_lookup_agent = Agent[CitizenContext](
    name="Service Lookup Agent",
    handoff_description="A helpful agent that can find suitable government services for a given citizens's life situation.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are a government service lookup agent. You were transferred from the triage agent because the citizen describes their life situation they need to help with.
    The citizen speaks Czech, you answer in Czech.
    It is crucial to personalize the output for the citizen by considering their personal details (name, age) and contextualize it for their life situation.
    Use the following routine to support the citizen:
    # Routine
    1. Identify the citizen's life situation based on the previous messages and construct its description. Use the words of the citizen based on the previous conversation, but try to focus it factually as the citizen may be upset, confused or stressed. The citizen will probably describe their life situation in a vague way, so try to enrich it with relevant phrases and details that describe their situation with different words and from different angles. Use this extended and enriched description to search for relevant government services.
    2. Use the `service_lookup_tool_semantic` to search for government services based on the description. It is recommended to set the `k` parameter to 10, but it can be adjusted to return more results if needed.
    3. If you find no service, ask the citizen to better specify their life situation and repeat the routine from step 1.
    4. If you find services, check if they are relevant to the citizen's problem by comparing their descriptions with the citizen's life situation.
    5. If there is no relevant service, ask the citizen to better specify their life situation and repeat the routine from step 1.
    6. List the relevant services to the citizen, including their names, IDs and short explanations of how they can help the citizen in their concrete life situation in the following form:
    **[service name]**
      - ID: [service id]
      - Vysvětlení: [short personalized explanation contextualized for the life situation]
    7. If the citizen needs more detailed information about a specific service, transfer back to the triage agent.
    8. If the citizen starts asking about other services or life situations, transfer back to the triage agent.
    """,
    tools=[service_lookup_tool_semantic],
    model="gpt-4o"
)

service_detail_agent = Agent[CitizenContext](
    name="Service Detail Agent",
    handoff_description="A helpful agent that can provide detailed information about a specific government service personalized for the citizen and their concrete life situation.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are a government service guide agent.
    You were transferred from the triage agent because the citizen needs detailed information about how to solve their life situation using a specific government service.
    The citizen speaks Czech, you answer in Czech.
    Answer solely based on the details of the given governmental service contextualiyzed for the life situation.
    Use the following routine to support the citizen:
    # Routine
    1. Identify the service ID from the citizen's previous conversation. The citizen can ask for the service directly by its ID or by using its name or by textual description refering to the service mentioned during the conversation.
    2. If the service ID cannot be identified, ask the citizen to provide the service ID or name again and repeat the routine from step 1.
    3. Use the `service_detail_tool` tool to retrieve detailed information about the service.
    4. Using solely the detailed service information, provide the summary of the service about how the service can help the citizen in their life situation.
    5. Ask the citizen if they have a question about the service.
    6. If the citizen has a factual question about the service, answer it based on the service details.
    7. If the citizen needs help to resolve their life situation using the service, transfer to the authority communication agent.
    8. If the citizen starts asking about other services or life situations, transfer back to the triage agent.
    """,
    tools=[service_detail_tool],
    model="gpt-4.1-mini"
)

authority_agent = Agent[CitizenContext](
    name="Authority Agent",
    handoff_description="A helpful agent that represents the authority providing the service to the citizen who needs to resolve their life situation using the service.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are the authority that provides the service to the citizen.
    You were transferred from the triage agent because the citizen needs to resolve their life situation using the service.
    You are not the real authority, but you simulate the communication with the authority based on the service steps and details.
    The citizen must feel that they are communicating with the authority that provides the service to them.
    Do not reveal that you are not the real authority.
    The citizen speaks Czech. You speak in Czech.
    Use the following routine:
    # Routine
    1. Identify the service ID from the citizen's previous conversation. The citizen can ask for the service directly by its ID or by using its name or by textual description refering to the service mentioned during the conversation.
    2. If the service ID cannot be identified, ask the citizen to provide the service ID or name again and repeat the routine from step 1.
    3. Use the `service_steps_tool` tool to retrieve the steps needed to resolve the citizen's life situation using the service. It may also give you additional information on how to perform the steps and what informaion or documents are needed from the citizen. Do not output anything to the citizen yet.
    4. Simulate the authority communicating with the citizen based on the retrieved steps - one by one. Stop at each step and do one of the following:
      - If the step needs additional information or documents from the citizen, ask the citizen to provide them and wait for their response. You can search the web to find out questionaires, forms, templates or examples showing what kind and structure of information is needed.
      - If a step describes an action of the authority, do the action and inform the citizen about the result
    5. Ff all steps are completed, inform the citizen that their life situation is resolved and provide a summary of the steps taken.
    6. If the citizen has further questions or needs assistance, offer to help them with any additional information but do not provide nothing outside the service details.
    7. If the citizen starts asking about other services or life situations, transfer back to the triage agent.
    """,
    tools=[service_steps_tool, WebSearchTool(user_location={"type": "approximate", "country": "CZ"})],
    model="o4-mini-2025-04-16"
)

triage_agent = Agent[CitizenContext](
    name="Triage Agent",
    handoff_description="A triage agent that can delegate a citizen's request to the appropriate agent.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are a helpful triaging agent.
    You only delegate the citizen's request to the appropriate agent based on the citizen's request.
    """,
    handoffs=[
        service_lookup_agent,
        service_detail_agent,
        authority_agent
    ],
    model="gpt-4.1-mini"
)

service_lookup_agent.handoffs.append(triage_agent)
service_detail_agent.handoffs.append(triage_agent)
service_detail_agent.handoffs.append(authority_agent)
authority_agent.handoffs.append(triage_agent)

async def main():
    current_agent: Agent[CitizenContext] = triage_agent
    input_items: list[TResponseInputItem] = []
    context = CitizenContext()
    context.citizen_name = "Jan Novák"
    context.citizen_age = 47

    conversation_id = uuid.uuid4().hex[:16]

    while True:
        user_input = input("[AGENTIC AI] *** S čím vám mohu pomoci?: ")
        #with trace("Citizen assistant", group_id=conversation_id):
        input_items.append({"content": user_input, "role": "user"})
        result = await Runner.run(current_agent, input_items, context=context)
        for new_item in result.new_items:
            agent_name = new_item.agent.name
            if isinstance(new_item, MessageOutputItem):
                print(f"[AGENTIC AI] {agent_name} *** {ItemHelpers.text_message_output(new_item)}")
            elif isinstance(new_item, HandoffOutputItem):
                print(
                    f"[AGENTIC AI] Handed off from {new_item.source_agent.name} to {new_item.target_agent.name}"
                )
            elif isinstance(new_item, ToolCallItem):
                tool_name = getattr(new_item.raw_item, 'name', None) or getattr(new_item.raw_item, 'function', {}).get('name', 'unknown tool')
                print(f"[AGENTIC AI] {agent_name}: Calling a tool {tool_name}")
            elif isinstance(new_item, ToolCallOutputItem):
                print(f"[AGENTIC AI] {agent_name}: Tool output received.")
            else:
                print(f"[AGENTIC AI] {agent_name}: Skipping item: {new_item.__class__.__name__}")
        input_items = result.to_input_list()
        current_agent = result.last_agent

if __name__ == "__main__":
    asyncio.run(main())