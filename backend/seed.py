import asyncio
import hashlib
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

import os
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://evalkit:evalkit@postgres:5432/evalkit")

async def seed():
    engine = create_async_engine(DATABASE_URL)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        from app.models import Organization, User, Project, GatePolicy, APIKey

        # Create organization
        org_id = uuid.uuid4()
        org = Organization(
            id=org_id,
            name="Test Organization",
            slug="test-org",
            plan_type="pro"
        )
        session.add(org)
        await session.flush()  # Ensure org exists before user references it

        # Create user
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            clerk_user_id="test_user_001",
            email="test@example.com",
            name="Test User",
            organization_id=org_id,
            role="owner"
        )
        session.add(user)
        await session.flush()  # Ensure user exists before API key references it

        # Create project
        project_id = uuid.uuid4()
        project = Project(
            id=project_id,
            name="My RAG App",
            slug="my-rag-app",
            description="Test RAG application",
            organization_id=org_id
        )
        session.add(project)
        await session.flush()  # Ensure project exists before gate policy references it

        # Create gate policy
        policy = GatePolicy(project_id=project_id)
        session.add(policy)

        # Create API key
        raw_key = "pk_test_evalkit123456789"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        api_key = APIKey(
            key_hash=key_hash,
            key_prefix="pk_test_",
            name="Test API Key",
            organization_id=org_id,
            created_by=user_id,
            scopes=["evaluate:write", "projects:read"]
        )
        session.add(api_key)

        await session.commit()

        print("Seed data created!")
        print(f"Organization ID: {org_id}")
        print(f"Project ID: {project_id}")
        print(f"API Key: {raw_key}")

if __name__ == "__main__":
    asyncio.run(seed())
