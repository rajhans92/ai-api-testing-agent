from langgraph.graph import StateGraph, START, END
from langchain.chat_models import init_chat_model
from langchain_core.prompts import PromptTemplate
from typing_extensions import TypedDict
from sqlalchemy.orm import Session
from app.utils.config import (
    LLM_MODEL,
    OPENAI_API_KEY
)
from app.models.apiParser import (
     API,
     APIParameter,
     APIResponse
)
from app.services.promptService import (
    loadPrompt
)
llm = init_chat_model(model=LLM_MODEL, api_key=OPENAI_API_KEY)

# Graph state
class State(TypedDict):
    swaggerId: str
    db: Session


def createDependencyGraph(state: State):
        swaggerId = state["swaggerId"]
        db = state["db"]
        # Fetch API details from database using swaggerId, use LLM to create dependency graph,
        apiList = (db.query(API, APIParameter)
                    .join(
                        APIParameter,
                        API.id == APIParameter.api_id
                    )
                    .filter(
                        API.swagger_id == swaggerId
                    )
                    .all())
        sourceApiDetiails= {}
        setOfDependency = {}
        for api in apiList:
            sourceApiDetiails = {
                "sourceApiId" : api.id,
                "unique_path" : api.unique_path,
                "method" : api.method,
                "path" : api.path,
                "summary" : api.summary,
                "description" : api.description,
                "requestBody" : api.row_json,
                "location" : api.location,
                "required" : api.required
            }
            print(f"Source API Details: {sourceApiDetiails}")
            print("--------------------------------------------------")
            print("---------------------------------------------------")
            for key, value in sourceApiDetiails["requestBody"]:
                print(f"Source API requestBody: {key} : {value}")
                print("--------------------------------------------------")
                print("---------------------------------------------------")
                requestDetailApi = (
                                    db.query(API, APIResponse)
                                    .join(
                                        APIResponse,
                                        API.id == APIResponse.api_id
                                    )
                                    .filter(
                                        API.swagger_id == swaggerId,
                                        API.schema.ilike(f"%{key}%")
                                    )
                                    .all()
                                )
                for apiDepend in requestDetailApi:
                    setOfDependency[apiDepend.unique_path] = {
                            "id": apiDepend.id,
                            "method": apiDepend.method,
                            "path": apiDepend.path,
                            "summary": apiDepend.summary,
                            "description": apiDepend.description,
                            "response_schema": apiDepend.schema

                    }
                    print(f"Dependent API Details: {setOfDependency[apiDepend.unique_path]}")
                    print("--------------------------------------------------")
                    print("---------------------------------------------------")
            prompt = loadPrompt("dependencyPrompt.txt", sourceApiDetails=sourceApiDetiails, setOfDependency=setOfDependency)
            chain = llm | prompt
            response = chain.invoke()

            print(f"Dependency graph for API {api.id}: {response}")
            print("--------------------------------------------------")
            print("--------------------------------------------------")
            print("--------------------------------------------------")
            break
                  

def executeApiAndTest(state: State):
    # Execute APIs based on dependency graph and run tests, update state with results
    pass

def failerHandler(state: State):
    # Analyze failed tests and update state with failure details
    pass

def reevaluateDependencyGraph(state: State):
    # Use LLM to analyze failure details and suggest updates to dependency graph, update state
    pass


apiParserGraph = StateGraph(State)

apiParserGraph.add_node("createDependencyGraph",createDependencyGraph)
apiParserGraph.add_node("executeApiAndTest",executeApiAndTest)
apiParserGraph.add_node("reevaluateDependencyGraph",reevaluateDependencyGraph)
apiParserGraph.add_node("failerHandler",failerHandler)

# Add edges to connect nodes
apiParserGraph.add_edge(START, "createDependencyGraph")
apiParserGraph.add_edge("createDependencyGraph", "executeApiAndTest")
apiParserGraph.add_edge("executeApiAndTest", "failerHandler")
apiParserGraph.add_edge("failerHandler", "reevaluateDependencyGraph")
apiParserGraph.add_edge("failerHandler", "executeApiAndTest")
apiParserGraph.add_edge("reevaluateDependencyGraph", "executeApiAndTest")
apiParserGraph.add_edge("executeApiAndTest", END)

apiParserAgent = apiParserGraph.compile()

async def executeAPIParserAgent(swaggerId: int, db: Session):
        print(f"Executing API Parser Agent with swaggerId: {swaggerId}")
        await apiParserAgent.invoke({swaggerId: swaggerId, db:db})
        print("API Parser Agent execution completed.")
