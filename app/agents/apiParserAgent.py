from langgraph.graph import StateGraph, START, END
from langchain.chat_models import init_chat_model
from langchain_core.prompts import PromptTemplate
from typing_extensions import TypedDict
from app.utils.config import (
    LLM_MODEL,
    OPENAI_API_KEY
)
from app.services.handler import get_api_parser_service

llm = init_chat_model(model=LLM_MODEL, api_key=OPENAI_API_KEY)

# Graph state
class State(TypedDict):
    api: str


apiParserGraph = StateGraph(State)

apiParserGraph.add_node("getSwaggerApiDetails",getSwaggerApiDetails)
apiParserGraph.add_node("createDependencyGraph",createDependencyGraph)
apiParserGraph.add_node("executeApiAndTest",executeApiAndTest)
apiParserGraph.add_node("reevaluateDependencyGraph",reevaluateDependencyGraph)
apiParserGraph.add_node("failerHandler",failerHandler)

# Add edges to connect nodes
apiParserGraph.add_edge(START, "getSwaggerApiDetails")
apiParserGraph.add_edge("getSwaggerApiDetails", "createDependencyGraph")
apiParserGraph.add_edge("createDependencyGraph", "executeApiAndTest")
apiParserGraph.add_edge("executeApiAndTest", "failerHandler")
apiParserGraph.add_edge("failerHandler", "reevaluateDependencyGraph")
apiParserGraph.add_edge("failerHandler", "executeApiAndTest")
apiParserGraph.add_edge("reevaluateDependencyGraph", "executeApiAndTest")
apiParserGraph.add_edge("executeApiAndTest", END)

apiParserAgent = apiParserGraph.compile()

async def executeAPIParserAgent(swaggerId: int):
        await apiParserAgent.invoke({swaggerId: swaggerId})

def getSwaggerApiDetails(state: State):
    # Fetch swagger details from DB using swaggerId and update state
    pass

def createDependencyGraph(state: State):
    # Create initial dependency graph based on swagger details and update state
    pass

def executeApiAndTest(state: State):
    # Execute APIs based on dependency graph and run tests, update state with results
    pass

def failerHandler(state: State):
    # Analyze failed tests and update state with failure details
    pass

def reevaluateDependencyGraph(state: State):
    # Use LLM to analyze failure details and suggest updates to dependency graph, update state
    pass



