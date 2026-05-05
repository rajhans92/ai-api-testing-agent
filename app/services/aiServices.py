from langchain.chat_models import init_chat_model
from langchain_core.prompts import PromptTemplate   
from app.schemas.llmParser import DependencyResponse 
from app.utils.config import (
    LLM_MODEL,
    OPENAI_API_KEY
)

llm = init_chat_model(model=LLM_MODEL, api_key=OPENAI_API_KEY)
structured_llm = llm.with_structured_output(DependencyResponse)

def infer_dependencies_with_llm(api_map, calculated_dependencies_by_logic):
    prompt = PromptTemplate(
        input_variables=["api_map", "calculated_dependencies_by_logic"],
        template="""
                    You are an expert API dependency analyzer and reviewer.

                    Your task is to analyze and CORRECT the given API dependencies.

                    You are given:
                    1. API Map → contains API details (path, method, parameters, responses)
                    2. Existing Dependencies → generated using rule-based logic (may contain errors)

                    ----------------------------------------
                    YOUR RESPONSIBILITIES
                    ----------------------------------------

                    1. VALIDATE existing dependencies:
                    - Remove incorrect dependencies
                    - Fix wrong direction if needed

                    2. IDENTIFY missing dependencies:
                    - Add new dependencies if strong logical relationship exists

                    3. RETURN a FINAL CLEAN dependency set:
                    - Include ONLY correct dependencies
                    - Do NOT return duplicates
                    - Do NOT return invalid or weak dependencies

                    ----------------------------------------
                    STRICT RULES
                    ----------------------------------------

                    A dependency exists ONLY if:
                    - One API produces data (token, id, resource)
                    - Another API requires or logically depends on that data

                    Focus on:
                    - Authentication flow (login → token → protected APIs)
                    - Resource lifecycle (create → get/update/delete)
                    - ID/data propagation across APIs

                    IGNORE:
                    - Weak name matching (e.g., same parameter names without meaning)
                    - Generic fields like status, message

                    Direction MUST be:
                    api_id → depends_on_api_id  
                    (api_id depends on depends_on_api_id)

                    ----------------------------------------
                    INPUT
                    ----------------------------------------

                    API Map:
                    {api_map}

                    Existing Dependencies:
                    {calculated_dependencies_by_logic}

                    ----------------------------------------
                    OUTPUT
                    ----------------------------------------

                    Return the FINAL corrected dependency list only.
                    Do not include explanation.
            """
    )

    chain = prompt | structured_llm
    response = chain.invoke({
                    "api_map": api_map,
                    "calculated_dependencies_by_logic": calculated_dependencies_by_logic
                })
    print("LLM Dependency Analysis Response:", response)
    return response.dependencies