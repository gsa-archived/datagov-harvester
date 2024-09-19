import json
import logging
import os
from pathlib import Path
from typing import Any, Generator, List
from unittest.mock import patch

import pytest
from dotenv import load_dotenv
from flask import Flask
from sqlalchemy.orm import scoped_session, sessionmaker

from app import create_app
from app.scripts.load_manager import create_future_date
from database.interface import HarvesterDBInterface
from database.models import HarvestJob, HarvestSource, Organization, db
from harvester.utils.general_utils import dataset_to_hash, sort_dataset

load_dotenv()

logger = logging.getLogger("pytest.conftest")

EXAMPLE_DATA = Path(__file__).parents[1] / "example_data"

HARVEST_SOURCE_URL = os.getenv("HARVEST_SOURCE_URL")

# ignore tests in the functional dir
collect_ignore_glob = ["functional/*"]


@pytest.fixture(scope="session", autouse=True)
def default_session_fixture():
    with patch("app.load_manager", lambda: True):
        yield


@pytest.fixture(scope="session")
def app() -> Generator[Any, Flask, Any]:
    app = create_app()
    app.config.update({"TESTING": True})
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    return app.test_client()


@pytest.fixture(scope="function")
def session(app) -> Generator[Any, scoped_session, Any]:
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()

        SessionLocal = sessionmaker(bind=connection, autocommit=False, autoflush=False)
        session = scoped_session(SessionLocal)
        yield session

        session.remove()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def interface(session) -> HarvesterDBInterface:
    return HarvesterDBInterface(session=session)


@pytest.fixture(scope="function", autouse=True)
def default_function_fixture(interface):
    logger.info("Patching core.feature.service")
    with patch("harvester.harvest.db_interface", interface), patch(
        "harvester.exceptions.db_interface", interface
    ), patch("app.scripts.load_manager.interface", interface), patch(
        "app.routes.db", interface
    ):
        yield
    logger.info("Patching complete. Unpatching")


@pytest.fixture
def fixtures_json():
    file = Path(__file__).parents[0] / "fixtures.json"
    with open(file, "r") as file:
        return json.load(file)


## ORGS
@pytest.fixture
def organization_data(fixtures_json) -> dict:
    return fixtures_json["organization"][0]


@pytest.fixture
def organization_data_orm(organization_data: dict) -> Organization:
    return Organization(**organization_data)


## HARVEST SOURCES
@pytest.fixture
def source_data_dcatus(fixtures_json) -> dict:
    return fixtures_json["source"][0]


@pytest.fixture
def source_data_dcatus_orm(source_data_dcatus: dict) -> HarvestSource:
    return HarvestSource(**source_data_dcatus)


@pytest.fixture
def source_data_dcatus_2(organization_data: dict) -> dict:
    return {
        "id": "3f2652de-91df-4c63-8b53-bfced20b276b",
        "name": "Test Source 2",
        "notification_emails": "email@example.com",
        "organization_id": organization_data["id"],
        "frequency": "daily",
        "url": f"{HARVEST_SOURCE_URL}/dcatus/dcatus_2.json",
        "schema_type": "type1",
        "source_type": "dcatus",
    }


@pytest.fixture
def source_data_dcatus_same_title(organization_data: dict) -> dict:
    return {
        "id": "50301cdb-5766-46ed-8f46-ca63844315a2",
        "name": "Test Source Same Title",
        "notification_emails": "email@example.com",
        "organization_id": organization_data["id"],
        "frequency": "daily",
        "url": f"{HARVEST_SOURCE_URL}/dcatus/dcatus_same_title.json",
        "schema_type": "type1",
        "source_type": "dcatus",
    }


@pytest.fixture
def source_data_waf(organization_data: dict) -> dict:
    return {
        "id": "55dca495-3b92-4fe4-b9c5-d433cbc3c82d",
        "name": "Test Source (WAF)",
        "notification_emails": "wafl@example.com",
        "organization_id": organization_data["id"],
        "frequency": "daily",
        "url": f"{HARVEST_SOURCE_URL}/waf/",
        "schema_type": "type1",
        "source_type": "waf",
    }


@pytest.fixture
def source_data_dcatus_invalid(organization_data: dict) -> dict:
    return {
        "id": "2bfcb047-70dc-435a-a46c-4dec5df7532d",
        "name": "Test Source ( Invalid Records )",
        "notification_emails": "invalid@example.com",
        "organization_id": organization_data["id"],
        "frequency": "daily",
        "url": f"{HARVEST_SOURCE_URL}/dcatus/missing_title.json",
        "schema_type": "type1",
        "source_type": "dcatus",
    }


@pytest.fixture
def source_data_dcatus_single_record(organization_data: dict) -> dict:
    return {
        "id": "2f2652de-91df-4c63-8b53-bfced20b276b",
        "name": "Single Record Test Source",
        "notification_emails": "email@example.com",
        "organization_id": organization_data["id"],
        "frequency": "daily",
        "url": f"{HARVEST_SOURCE_URL}/dcatus/dcatus_single_record.json",
        "schema_type": "type1",
        "source_type": "dcatus",
    }


@pytest.fixture
def source_data_dcatus_bad_url(organization_data: dict) -> dict:
    return {
        "id": "b059e587-a4a1-422e-825a-830b4913dbfb",
        "name": "Bad URL Source",
        "notification_emails": "bad@example.com",
        "organization_id": organization_data["id"],
        "frequency": "daily",
        "url": f"{HARVEST_SOURCE_URL}/dcatus/bad_url.json",
        "schema_type": "type1",
        "source_type": "dcatus",
    }


@pytest.fixture
def source_data_dcatus_invalid_records(organization_data) -> dict:
    return {
        "id": "8e7f539b-0a83-43ad-950e-3976bb11a425",
        "name": "Invalid Record Source",
        "notification_emails": "invalid_record@example.com",
        "organization_id": organization_data["id"],
        "frequency": "daily",
        "url": "http://localhost/dcatus/missing_title.json",
        "schema_type": "type1",
        "source_type": "dcatus",
    }


## HARVEST JOBS
@pytest.fixture
def job_data_dcatus(fixtures_json) -> dict:
    return fixtures_json["job"][0]


@pytest.fixture
def job_data_dcatus_orm(job_data_dcatus: dict) -> HarvestJob:
    return HarvestJob(**job_data_dcatus)


@pytest.fixture
def job_data_dcatus_2(source_data_dcatus_2: dict) -> dict:
    return {
        "id": "392ac4b3-79a6-414b-a2b3-d6c607d3b8d4",
        "status": "new",
        "harvest_source_id": source_data_dcatus_2["id"],
    }


@pytest.fixture
def job_data_waf(source_data_waf: dict) -> dict:
    return {
        "id": "963cdc51-94d5-425d-a688-e0a57e0c5dd2",
        "status": "new",
        "harvest_source_id": source_data_waf["id"],
    }


@pytest.fixture
def job_data_dcatus_invalid(source_data_dcatus_invalid: dict) -> dict:
    return {
        "id": "59df7ba5-102d-4ae3-abd6-01b7eb26a338",
        "status": "new",
        "harvest_source_id": source_data_dcatus_invalid["id"],
    }


@pytest.fixture
def job_data_dcatus_bad_url(source_data_dcatus_bad_url: dict) -> dict:
    return {
        "id": "707aee7b-bf72-4e07-a5fc-68980765b214",
        "status": "new",
        "harvest_source_id": source_data_dcatus_bad_url["id"],
    }


@pytest.fixture
def source_data_dcatus_invalid_records_job(
    source_data_dcatus_invalid_records: dict,
) -> dict:
    return {
        "id": "2b57046b-cfda-4a37-bf84-a4766a54a743",
        "status": "new",
        "harvest_source_id": source_data_dcatus_invalid_records["id"],
    }


## HARVEST JOB ERRORS
@pytest.fixture
def job_error_data(fixtures_json) -> dict:
    return fixtures_json["job_error"][0]


## HARVEST RECORDS
@pytest.fixture
def record_data_dcatus(fixtures_json) -> List[dict]:
    return fixtures_json["record"]


@pytest.fixture
def record_data_dcatus_2(job_data_dcatus_2):
    return [
        {
            "id": "72bae4b2-336e-49df-bc4c-410dc73dc316",
            "identifier": "test_identifier-2",
            "harvest_job_id": job_data_dcatus_2["id"],
            "harvest_source_id": job_data_dcatus_2["harvest_source_id"],
            "action": "create",
            "status": "error",
            "source_raw": "example data 2",
        }
    ]


## HARVEST RECORD ERRORS
@pytest.fixture
def record_error_data(fixtures_json) -> List[dict]:
    return fixtures_json["record_error"]


@pytest.fixture
def record_error_data_2(record_data_dcatus_2) -> dict:
    return [
        {
            "harvest_record_id": record_data_dcatus_2[0]["id"],
            "message": "record is invalid",
            "type": "ValidationException",
        }
    ]


@pytest.fixture
def interface_no_jobs(interface, organization_data, source_data_dcatus):
    interface.add_organization(organization_data)
    interface.add_harvest_source(source_data_dcatus)

    return interface


@pytest.fixture
def interface_with_fixture_json(
    interface_no_jobs,
    job_data_dcatus,
    job_error_data,
    record_data_dcatus,
    record_error_data,
):
    interface_no_jobs.add_harvest_job(job_data_dcatus)
    interface_no_jobs.add_harvest_job_error(job_error_data)
    for record in record_data_dcatus:
        interface_no_jobs.add_harvest_record(record)
    for error in record_error_data:
        interface_no_jobs.add_harvest_record_error(error)

    return interface_no_jobs


@pytest.fixture
def interface_with_multiple_sources(
    interface_with_fixture_json,
    source_data_dcatus_2,
    job_data_dcatus_2,
    record_data_dcatus_2,
    record_error_data_2,
):
    interface_with_fixture_json.add_harvest_source(source_data_dcatus_2)
    interface_with_fixture_json.add_harvest_job(job_data_dcatus_2)
    for record in record_data_dcatus_2:
        interface_with_fixture_json.add_harvest_record(record)
    for error in record_error_data_2:
        interface_with_fixture_json.add_harvest_record_error(error)

    return interface_with_fixture_json


## MISC
@pytest.fixture
def interface_with_multiple_jobs(interface_no_jobs, source_data_dcatus):
    statuses = ["new", "in_progress", "complete", "error"]
    frequencies = ["daily", "monthly"]
    jobs = [
        {
            "status": status,
            "harvest_source_id": source_data_dcatus["id"],
            "date_created": create_future_date(frequency),
        }
        for status in statuses
        for frequency in frequencies
    ]
    jobs_2 = [
        {
            "status": status,
            "harvest_source_id": source_data_dcatus["id"],
        }
        for status in statuses
    ]

    for job in jobs + jobs_2:
        interface_no_jobs.add_harvest_job(job)

    return interface_no_jobs


@pytest.fixture
def latest_records(
    source_data_dcatus, source_data_dcatus_2, job_data_dcatus, job_data_dcatus_2
):
    return [
        {
            "identifier": "a",
            "date_created": "2024-01-01T00:00:00.001Z",
            "source_raw": "data",
            "status": "success",
            "action": "create",
            "harvest_source_id": source_data_dcatus["id"],
            "harvest_job_id": job_data_dcatus["id"],
        },
        {
            "identifier": "a",
            "date_created": "2024-03-01T00:00:00.001Z",
            "source_raw": "data_1",
            "status": "success",
            "action": "update",
            "harvest_source_id": source_data_dcatus["id"],
            "harvest_job_id": job_data_dcatus["id"],
        },
        {
            "identifier": "b",
            "date_created": "2024-03-01T00:00:00.001Z",
            "source_raw": "data_10",
            "status": "success",
            "action": "create",
            "harvest_source_id": source_data_dcatus["id"],
            "harvest_job_id": job_data_dcatus["id"],
        },
        {
            "identifier": "b",
            "date_created": "2022-05-01T00:00:00.001Z",
            "source_raw": "data_30",
            "status": "error",
            "action": "update",
            "harvest_source_id": source_data_dcatus["id"],
            "harvest_job_id": job_data_dcatus["id"],
        },
        {
            "identifier": "c",
            "date_created": "2024-05-01T00:00:00.001Z",
            "source_raw": "data_12",
            "status": "success",
            "action": "create",
            "harvest_source_id": source_data_dcatus["id"],
            "harvest_job_id": job_data_dcatus["id"],
        },
        {
            "identifier": "d",
            "date_created": "2024-05-01T00:00:00.001Z",
            "source_raw": "data_2",
            "status": "success",
            "action": "delete",
            "harvest_source_id": source_data_dcatus["id"],
            "harvest_job_id": job_data_dcatus["id"],
        },
        {
            "identifier": "d",
            "date_created": "2024-04-01T00:00:00.001Z",
            "source_raw": "data_5",
            "status": "success",
            "action": "create",
            "harvest_source_id": source_data_dcatus["id"],
            "harvest_job_id": job_data_dcatus["id"],
        },
        {
            "identifier": "e",
            "date_created": "2024-04-01T00:00:00.001Z",
            "source_raw": "data_123",
            "status": "success",
            "action": "create",
            "harvest_source_id": source_data_dcatus["id"],
            "harvest_job_id": job_data_dcatus["id"],
        },
        {
            "identifier": "e",
            "date_created": "2024-04-02T00:00:00.001Z",
            "source_raw": "data_123",
            "status": "success",
            "action": "delete",
            "harvest_source_id": source_data_dcatus["id"],
            "harvest_job_id": job_data_dcatus["id"],
        },
        {
            "identifier": "e",
            "date_created": "2024-04-03T00:00:00.001Z",
            "source_raw": "data_123",
            "status": "success",
            "action": "create",
            "harvest_source_id": source_data_dcatus["id"],
            "harvest_job_id": job_data_dcatus["id"],
        },
        {
            "identifier": "f",
            "date_created": "2024-04-03T00:00:00.001Z",
            "source_raw": "data_123",
            "status": "success",
            "action": "create",
            "harvest_source_id": source_data_dcatus_2["id"],
            "harvest_job_id": job_data_dcatus_2["id"],  #
        },
    ]


@pytest.fixture
def internal_compare_data(job_data_dcatus: dict) -> dict:
    # ruff: noqa: E501
    return {
        "job_id": job_data_dcatus["id"],
        "harvest_source_id": job_data_dcatus["harvest_source_id"],
        "records": [
            {
                "contactPoint": {
                    "fn": "Harold W. Hild",
                    "hasEmail": "mailto:hhild@CFTC.GOV",
                },
                "describedBy": "https://www.cftc.gov/MarketReports/CommitmentsofTraders/ExplanatoryNotes/index.htm",
                "description": "COT reports provide a breakdown of each Tuesday's open interest for futures and options on futures market in which 20 or more traders hold positions equal to or above the reporting levels established by CFTC",
                "distribution": [
                    {
                        "accessURL": "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm"
                    }
                ],
                "modified": "R/P1W",
                "programCode": ["000:000"],
                "publisher": {
                    "name": "U.S. Commodity Futures Trading Commission",
                    "subOrganizationOf": {"name": "U.S. Government"},
                },
                "title": "Commitment of Traders",
                "accessLevel": "public",
                "bureauCode": ["339:00"],
                "identifier": "cftc-dc10",
                "keyword": ["commitment of traders", "cot", "open interest"],
            },
            {
                "accessLevel": "public",
                "bureauCode": ["339:00"],
                "contactPoint": {
                    "fn": "Harold W. Hild",
                    "hasEmail": "mailto:hhild@CFTC.GOV",
                },
                "describedBy": "https://www.cftc.gov/MarketReports/BankParticipationReports/ExplanatoryNotes/index.htm",
                "description": "The Bank Participation Report (BPR), developed by the Division of Market Oversight to provide the U.S. banking authorities and the Bank for International Settlements (BIS, located in Basel, Switzerland) aggregate large-trader positions of banks participating in various financial and non-financial commodity futures.",
                "distribution": [
                    {
                        "accessURL": "https://www.cftc.gov/MarketReports/BankParticipationReports/index.htm"
                    }
                ],
                "identifier": "cftc-dc2",
                "keyword": ["bank participation report", "bpr", "banking", "new value"],
                "modified": "R/P1M",
                "programCode": ["000:000"],
                "publisher": {
                    "name": "U.S. Commodity Futures Trading Commission",
                    "subOrganizationOf": {"name": "U.S. Government"},
                },
                "title": "Bank Participation Reports",
            },
        ],
    }


@pytest.fixture
def single_internal_record(internal_compare_data):
    record = internal_compare_data["records"][0]
    return {
        "identifier": record["identifier"],
        "harvest_job_id": internal_compare_data["job_id"],
        "harvest_source_id": internal_compare_data["harvest_source_id"],
        "source_hash": dataset_to_hash(sort_dataset(record)),
        "status": "success",
        "action": "create",
    }


@pytest.fixture
def dhl_cf_task_data() -> dict:
    return {
        "app_guuid": "f4ab7f86-bee0-44fd-8806-1dca7f8e215a",
        "task_id": "cf_task_integration",
        "command": "/usr/bin/sleep 60",
    }
