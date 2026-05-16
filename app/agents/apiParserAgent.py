from langgraph.graph import StateGraph, START, END
from langchain.chat_models import init_chat_model
from typing_extensions import TypedDict
from sqlalchemy.orm import Session
from sqlalchemy import select,String
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
    swaggerId: int
    db: Session


async def createDependencyGraph(state: State):
        swaggerId = state["swaggerId"]
        db = state["db"]
        # Fetch API details from database using swaggerId, use LLM to create dependency graph,
        print(f"Fetching API details for swaggerId: {swaggerId}")
        stmt = (
            select(API, APIParameter)
            .join(
                APIParameter,
                API.id == APIParameter.api_id
            )
            .where(
                API.swagger_id == swaggerId
            )
        )

        result = await db.execute(stmt)

        apiList = result.all()
        print(f"Fetched {len(apiList)} APIs for swaggerId: {swaggerId}")
        sourceApiDetiails= {}
        setOfDependency = {}
        run = 0
        for api_obj, param_obj in apiList:
            if(run >= 5):
                break
            run += 1
            sourceApiDetiails = {
                "sourceApiId": api_obj.id,
                "unique_path": api_obj.unique_path,
                "method": api_obj.method,
                "path": api_obj.path,
                "summary": api_obj.summary,
                "description": api_obj.description,
                "requestBody": param_obj.schema,
                "location": param_obj.location,
                "required": param_obj.required
            }
            print(f"Source API Details: {sourceApiDetiails}")
            print("--------------------------------------------------")
            print("---------------------------------------------------")
            for key, value in sourceApiDetiails["requestBody"].items():
                # print(f"Source API requestBody: {key} : {value}")
                # print("--------------------------------------------------")
                # print("---------------------------------------------------")
                
                stmt = (
                    select(API, APIResponse)
                    .join(
                        APIResponse,
                        API.id == APIResponse.api_id
                    )
                    .filter(
                        API.swagger_id == swaggerId,
                        APIResponse.schema.cast(String).ilike(f"%{key}%")
                    )
                )

                result = await db.execute(stmt)

                requestDetailApi = result.all()

                for api_depend_obj, response_obj in requestDetailApi:
                    setOfDependency[api_depend_obj.unique_path] = {
                        "id": api_depend_obj.id,
                        "method": api_depend_obj.method,
                        "path": api_depend_obj.path,
                        "summary": api_depend_obj.summary,
                        "description": api_depend_obj.description,
                        "response_schema": response_obj.schema
                    }
                    # print(f"Dependent API Details: {setOfDependency[api_depend_obj.unique_path]}")
                #     print(f" unique_path = {api_depend_obj.unique_path}")
                # print (f" Count = {len(setOfDependency)}")
                # print("--------------------------------------------------")
                # print("---------------------------------------------------")
            prompt = loadPrompt("dependencyPrompt.txt", sourceApiDetails=sourceApiDetiails, setOfDependency=setOfDependency)
            print(f"Prompt for API {api_obj.id}: {prompt}")
            response = await llm.ainvoke(prompt)

            print(f"Dependency graph for API {api_obj.id}")
            print(response.content)
            print("--------------------------------------------------")
            print("--------------------------------------------------")
            print("--------------------------------------------------")
                  

async def executeApiAndTest(state: State):
    # Execute APIs based on dependency graph and run tests, update state with results
    pass

async def failerHandler(state: State):
    # Analyze failed tests and update state with failure details
    pass

async def reevaluateDependencyGraph(state: State):
    # Use LLM to analyze failure details and suggest updates to dependency graph, update state
    pass


apiParserGraph = StateGraph(State)

apiParserGraph.add_node("createDependencyGraph",createDependencyGraph)
apiParserGraph.add_node("executeApiAndTest",executeApiAndTest)
apiParserGraph.add_node("reevaluateDependencyGraph",reevaluateDependencyGraph)
apiParserGraph.add_node("failerHandler",failerHandler)

# Add edges to connect nodes
apiParserGraph.add_edge(START, "createDependencyGraph")
apiParserGraph.add_edge("createDependencyGraph", END)

# apiParserGraph.add_edge("createDependencyGraph", "executeApiAndTest")
# apiParserGraph.add_edge("executeApiAndTest", "failerHandler")
# apiParserGraph.add_edge("failerHandler", "reevaluateDependencyGraph")
# apiParserGraph.add_edge("failerHandler", "executeApiAndTest")
# apiParserGraph.add_edge("reevaluateDependencyGraph", "executeApiAndTest")
# apiParserGraph.add_edge("executeApiAndTest", END)

apiParserAgent = apiParserGraph.compile()

async def executeAPIParserAgent(swaggerId: int, db: Session):
        try:
            print(f"Executing API Parser Agent with swaggerId: {swaggerId}")
            await apiParserAgent.ainvoke({"swaggerId": swaggerId, "db":db})
            print("API Parser Agent execution completed.")
        except Exception as e:
            print(e)

