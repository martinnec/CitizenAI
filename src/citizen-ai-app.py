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
    handoff,
    trace,
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
    print("Debug: Found services by keywords:", [service.name for service in services])
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
    services = store.search_services_by_keywords(keywords, k)
    print("Debug: Found services by life situation:", [service.name for service in services])
    return services

@function_tool
async def service_detail_tool(service_id: str) -> str:
    """
    Get detailed information about a specific service by its ID.
    
    :param service_id: The ID of the service to retrieve details for.
    :return: A string containing the detailed information about the service.
    """
    print("Debug: Asking for service detail: ", service_id)
    service_detail_str = store.get_service_detail_by_id(service_id)
    if service_detail_str:
        return service_detail_str
    else:
        return "Service not found."

service_lookup_agent_keywords = Agent[CitizenContext](
    name="Service Lookup by Keywords Agent",
    handoff_description="A helpful agent that can find government services based on citizens's life situation.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are a government service lookup agent. You were transferred from the triage agent because the citizen describes their life situation they need to help with.
    The citizen speaks Czech, you answer in Czech.
    Call the citizen by their name and augment the messages to the citizen appropriately their age, based on the context.
    Use the following routine to support the citizen:
    # Routine
    1. Identify the keywords that best characterize the citizen's life situation. These keywords should be short and specific, preferably single words, not keyphrases. Use at least 10 keywords to have a chance to find something.
    2. Use the `service_lookup_tool_keywords` to search for government services based on the identified keywords. It is recommended to set the `k` parameter to 10, but it can be adjusted to return more results if needed.
    3. If you find no service, ask the citizen to better specify their life situation and repeat the routine from step 1.
    4. If you find services, check if they are relevant to the citizen's problem by comparing their descriptions with the citizen's life situation.
    5. If there is no relevant service, ask the citizen to better specify their life situation and repeat the routine from step 1.
    6. List the relevant services to the citizen, including their names, IDs and short explanations of how they can help the citizen in their life situation.
    7. If the citizen needs more detailed information about a specific service, transfer back to the triage agent.
    """,
    tools=[service_lookup_tool_keywords],
    model="gpt-4o"
)

service_lookup_agent = Agent[CitizenContext](
    name="Service Lookup Agent",
    handoff_description="A helpful agent that can find government services based on citizens's life situation.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are a government service lookup agent. You were transferred from the triage agent because the citizen describes their life situation they need to help with.
    The citizen speaks Czech, you answer in Czech.
    Use the following routine to support the citizen:
    # Routine
    1. Identify the citizen's life situation based on the previous messages and construct its description. Use the words of the citizen based on the previous conversation, but try to focus it factually as the citizen may be upset, confused or stressed.
    2. Use the `service_lookup_tool_semantic` to search for government services based on the description. It is recommended to set the `k` parameter to 5, but it can be adjusted to return more results if needed.
    3. If you find no service, ask the citizen to better specify their life situation and repeat the routine from step 1.
    4. If you find services, check if they are relevant to the citizen's problem by comparing their descriptions with the citizen's life situation.
    5. If there is no relevant service, ask the citizen to better specify their life situation and repeat the routine from step 1.
    6. List the relevant services to the citizen, including their names, IDs and short explanations of how they can help the citizen in their concrete life situation. It is crucial to personalize the service information for the citizen by considering their personal details (name, age) and their life situation.
    7. If the citizen needs more detailed information about a specific service, transfer back to the triage agent.
    8. If the citizen starts asking about other services or life situations, transfer back to the triage agent.
    """,
    tools=[service_lookup_tool_semantic],
    model="gpt-4o"
)

service_guide_agent = Agent[CitizenContext](
    name="Service Guide Agent",
    handoff_description="A helpful agent that can provide detailed information about a specific government service personalized for the citizen's personal details and their concrete life situation.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are a government service guide agent. You were transferred from the triage agent service because the citizen needs detailed information about a specific service and how it can help them in their life situation.
    The citizen speaks Czech, you answer in Czech.
    Call the citizen by their name and augment the messages to the citizen appropriately their age, based on the context.
    Use the following routine to support the citizen:
    # Routine
    1. Identify the service ID from the citizen's request.
    2. Use the `service_detail_tool` tool to retrieve detailed information about the service.
    3. Personalize the service information for the citizen by considering their personal details (name, age) and their life situation.
    4. Guide the citizen through the service, explaining how it can help them and what steps they need to take to access it.
    5. If the citizen has further questions or needs assistance, offer to help them with any additional information or steps they need to take.
    6. If the citizen starts asking about other services or life situations, transfer back to the triage agent.
    """,
    tools=[service_detail_tool],
    model="gpt-4o"
)

triage_agent = Agent[CitizenContext](
    name="Triage Agent",
    handoff_description="A triage agent that can delegate a citizen's request to the appropriate agent. The citizen speaks Czech, you answer in Czech.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are a helpful triaging agent.
    Always greet the citizen by their name and augment the messages to the citizen appropriately their age, based on the context.
    You can use your tools to delegate questions to other appropriate agents.
    """,
    handoffs=[
        service_lookup_agent,
        service_guide_agent
    ]
)

service_lookup_agent.handoffs.append(triage_agent)
service_guide_agent.handoffs.append(triage_agent)

async def main():
    current_agent: Agent[CitizenContext] = triage_agent
    input_items: list[TResponseInputItem] = []
    context = CitizenContext()
    context.citizen_name = input("Zadejte své jméno: ")
    context.citizen_age = int(input("Zadejte svůj věk: "))

    conversation_id = uuid.uuid4().hex[:16]

    while True:
        user_input = input("S čím vám mohu pomoci?: ")
        #with trace("Citizen assistant", group_id=conversation_id):
        input_items.append({"content": user_input, "role": "user"})
        result = await Runner.run(current_agent, input_items, context=context)
        for new_item in result.new_items:
            agent_name = new_item.agent.name
            if isinstance(new_item, MessageOutputItem):
                print(f"{agent_name}: {ItemHelpers.text_message_output(new_item)}")
            elif isinstance(new_item, HandoffOutputItem):
                print(
                    f"Handed off from {new_item.source_agent.name} to {new_item.target_agent.name}"
                )
            elif isinstance(new_item, ToolCallItem):
                print(f"{agent_name}: Calling a tool")
            elif isinstance(new_item, ToolCallOutputItem):
                print(f"{agent_name}: Tool call output: {new_item.output}")
            else:
                print(f"{agent_name}: Skipping item: {new_item.__class__.__name__}")
        input_items = result.to_input_list()
        current_agent = result.last_agent

if __name__ == "__main__":
    asyncio.run(main())