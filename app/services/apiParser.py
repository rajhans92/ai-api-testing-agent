from app.models.apiParser import (
    Project,
)

class APIParserService:
    def __init__(self, db_session):
        self.db = db_session

    async def create_project(self, project_details):
        try:
            new_project = Project(
                name=project_details.project_name,
                description=project_details.project_description
            )
            self.db.add(new_project)
            await self.db.commit()
            await self.db.refresh(new_project)
            return new_project.id
        except Exception as e:
            await self.db.rollback()
            raise Exception("Error creating project: " + str(e))

    async def get_project(self, project_id):
        try:
            project = await self.db.get(Project, project_id)
            if not project:
                raise Exception("Project not found")
            return {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "created_at": project.created_at
            }
        except Exception as e:
            raise Exception("Error fetching project: " + str(e))
        
    def parse_swagger(self, swagger_json, project_id):
        # Implement parsing logic here
        # 1. Validate the swagger_json
        # 2. Extract API details and save to database
        # 3. Handle authentication schemes
        # 4. Identify dependencies between APIs
        pass

    def get_apis(self, project_id):
        # Fetch APIs for a given project from the database
        pass

    def get_api_details(self, api_id):
        # Fetch detailed information about a specific API
        pass